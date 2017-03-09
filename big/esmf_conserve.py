from __future__ import print_function
import ESMF
import netCDF4
import numpy
import sys
import argparse
from functools import reduce
import time
from mpi4py import MPI

# turn on logging
esmpy = ESMF.Manager(debug=True)

# rank of this processor
pe = MPI.COMM_WORLD.Get_rank()

# number of processes
nprocs = MPI.COMM_WORLD.Get_size()

LAT_INDEX, LON_INDEX = 1, 0

parser = argparse.ArgumentParser(description='Conservatively interpolate using ESMF')
parser.add_argument('--src_file', type=str, dest='src_file', default='coords_CF_ORCA12_GO6-2.nc',
                    help='Source data file name')
parser.add_argument('--src_field', type=str, dest='src_field', 
                    default='ocndepw',
                    help='Source data field name')
parser.add_argument('--src_lat_bounds', type=str, dest='src_lat_bounds', 
                    default='latw_bounds',
                    help='Source latitude cell boundary array')
parser.add_argument('--src_lon_bounds', type=str, dest='src_lon_bounds', 
                    default='lonw_bounds',
                    help='Source longitude cell boundary array')
parser.add_argument('--dst_file', type=str, dest='dst_file', default='dst.nc',
                    help='Destination data file name')
parser.add_argument('--plot', dest='plot', action='store_true', help='Plot')

args = parser.parse_args()

if args.src_file is '':
    print('ERROR: must provide source data file name')
    parser.print_help()
    sys.exit(1)

if args.dst_file is '':
    print('ERROR: must provide destination data file name')
    parser.print_help()
    sys.exit(1)

src_file = args.src_file.encode('UTF-8') # python3
dst_file = args.dst_file.encode('UTF-8') # python3
ndims = 2

def createData(filename, fieldname, coord_names):

    # read the netcdf file header
    nc = netCDF4.Dataset(filename)

    # get the local cell array sizes
    cellDims = numpy.array(nc.variables[coord_names['lat_bounds']].shape[:2], numpy.int32)

    # create the ESMF grid
    grid = ESMF.Grid(max_index=cellDims, coord_sys=ESMF.api.constants.CoordSys.SPH_DEG) #, num_peri_dims=1, periodic_dim=1)

    # create coordinates
    grid.add_coords(staggerloc=ESMF.StaggerLoc.CORNER, coord_dim=LAT_INDEX)
    grid.add_coords(staggerloc=ESMF.StaggerLoc.CORNER, coord_dim=LON_INDEX)
    
    # get the local start/end index sets and set the point coordinates
    iBeg0 = grid.lower_bounds[ESMF.StaggerLoc.CORNER][LON_INDEX]
    iEnd0 = grid.upper_bounds[ESMF.StaggerLoc.CORNER][LON_INDEX]
    iBeg1 = grid.lower_bounds[ESMF.StaggerLoc.CORNER][LAT_INDEX]
    iEnd1 = grid.upper_bounds[ESMF.StaggerLoc.CORNER][LAT_INDEX]

    # read the bound coordinates
    boundLats = nc.variables[coord_names['lat_bounds']][iBeg0:iEnd0 - 1, iBeg1:iEnd1 - 1, :]
    boundLons = nc.variables[coord_names['lon_bounds']][iBeg0:iEnd0 - 1, iBeg1:iEnd1 - 1, :]

    pointSizes = (boundLats.shape[0] + 1, boundLats.shape[1] + 1)

    # fill in the lat-lon ar the cell corner points
    lats = numpy.zeros(pointSizes, numpy.float64)
    lons = numpy.zeros(pointSizes, numpy.float64)

    lats[:-1, :-1] = boundLats[..., 0]
    lats[-1, :-1] = boundLats[-1, :, 1]
    lats[-1, -1]  = boundLats[-1, -1, 2]
    lats[:-1, -1]  = boundLats[:, -1, 3]

    lons[:-1, :-1] = boundLons[..., 0]
    lons[-1, :-1] = boundLons[-1, :, 1]
    lons[-1, -1]  = boundLons[-1, -1, 2]
    lons[:-1, -1]  = boundLons[:, -1, 3]
    
    coordLatsPoint = grid.get_coords(coord_dim=LAT_INDEX, staggerloc=ESMF.StaggerLoc.CORNER)
    coordLonsPoint = grid.get_coords(coord_dim=LON_INDEX, staggerloc=ESMF.StaggerLoc.CORNER)

    # set the ESMF coordinates
    coordLatsPoint[:] = lats
    coordLonsPoint[:] = lons

    # create and set the field, cell centred
    field = ESMF.Field(grid, staggerloc=ESMF.StaggerLoc.CENTER)

    # read the cell centred data and set the field. Note that we need to use the point dims
    field.data[...] = nc.variables[fieldname][iBeg0:iEnd0, iBeg1:iEnd1]

    return grid, field

timeStats = {
    'weights': float('nan'),
    'evaluation': float('nan'),
}

srcGrid, srcData = createData(src_file, args.src_field, {'lat_bounds': args.src_lat_bounds,
                                                                     'lon_bounds': args.src_lon_bounds,})
dstGrid, dstData = createData(dst_file, 'cellData', {'lat_bounds': 'latMid_bnds',
                                                                   'lon_bounds': 'lonMid_bnds',})

# save the reference (exact) field data
dstDataRef = dstData.data.copy()
dstData.data[...] = -1

# compute the interpolation weights
tic = time.time()
regrid = ESMF.Regrid(srcfield=srcData, dstfield=dstData,
                     regrid_method=ESMF.api.constants.RegridMethod.CONSERVE,
                     unmapped_action=ESMF.api.constants.UnmappedAction.IGNORE,
                     ignore_degenerate=True)
timeStats['weights'] = time.time() - tic

# interpolate
tic = time.time()
regrid(srcData, dstData)
timeStats['evaluation'] = time.time() - tic

# compute error
srcNtot = len(srcData.data.flat)
dstNtot = len(dstData.data.flat)
localSumError = numpy.sum(abs(dstData.data - dstDataRef))
globalSumError = numpy.sum(MPI.COMM_WORLD.gather(localSumError, root=0))
globalSrcNtot = numpy.sum(MPI.COMM_WORLD.gather(srcNtot, root=0))
globalDstNtot = numpy.sum(MPI.COMM_WORLD.gather(dstNtot, root=0))

globalTimeStats = {}
for k, v in timeStats.items():
    # max value
    ts = MPI.COMM_WORLD.gather(v, root=0)
    if ts is not None:
        globalTimeStats[k] = max(ts)

if pe == 0:
    error = globalSumError / float(globalDstNtot)
    print('esmf interpolation:')
    print('\tsrc: ntot: {}'.format(globalSrcNtot))
    print('\tdst: ntot: {}'.format(globalDstNtot))
    print('interpolation error: {:.3g}'.format(error))

    totTime = 0.0
    print('time stats:')
    for k, v in globalTimeStats.items():
        print('\t{0:<32} {1:>.3g} sec'.format(k, v))
        totTime += v
    print('\t{0:<32} {1:>.3g} sec'.format('total', totTime))

# plot
if args.plot and nprocs == 1:
    xPoint = dstGrid.get_coords(coord_dim=LON_INDEX, staggerloc=ESMF.StaggerLoc.CORNER)
    yPoint = dstGrid.get_coords(coord_dim=LAT_INDEX, staggerloc=ESMF.StaggerLoc.CORNER)
    xxCell = 0.25 * (xPoint[0:-1, 0:-1] + xPoint[1:, 0:-1] + xPoint[1:, 1:] + xPoint[0:-1, 1:])
    yyCell = 0.25 * (yPoint[0:-1, 0:-1] + yPoint[1:, 0:-1] + yPoint[1:, 1:] + yPoint[0:-1, 1:])

    from matplotlib import pylab
    pylab.pcolor(xxCell, yyCell, dstData.data, vmin=-1.0, vmax=1.0)
    pylab.show()
