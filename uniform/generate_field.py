import argparse
import numpy
import iris
import sys

iris.FUTURE.netcdf_no_unlimited = True

parser = argparse.ArgumentParser(description='Generate uniform data in 2d')
parser.add_argument('--src_nj', type=int, dest='src_nj', default=401, 
                    help='Source latitude axis dimension')
parser.add_argument('--src_ni', type=int, dest='src_ni', default=801, 
                    help='Source longitude axis dimension')
parser.add_argument('--dst_nj', type=int, dest='dst_nj', default=1201, 
                    help='Destination latitude axis dimension')
parser.add_argument('--dst_ni', type=int, dest='dst_ni', default=2401, 
                    help='Destination longitude axis dimension')
parser.add_argument('--src_file', type=str, dest='src_file', default='src.nc',
                    help='Source data file name')
parser.add_argument('--dst_file', type=str, dest='dst_file', default='dst.nc',
                    help='Destination data file name')

args = parser.parse_args()

if args.src_file is '':
    print('ERROR: must provide source data file name')
    parser.print_help()
    sys.exit(1)

if args.dst_file is '':
    print('ERROR: must provide destination data file name')
    parser.print_help()
    sys.exit(1)

latMin, latMax = -90.0, +90.0
lonMin, lonMax = 0.0, 360.0

# generate the axes
srcLats = numpy.linspace(latMin, latMax, args.src_nj)
srcLons = numpy.linspace(lonMin, lonMax, args.src_ni)
dstLats = numpy.linspace(latMin, latMax, args.dst_nj)
dstLons = numpy.linspace(lonMin, lonMax, args.dst_ni)
srcData = numpy.zeros((args.src_nj, args.src_ni), numpy.float64)
dstData = numpy.zeros((args.dst_nj, args.dst_ni), numpy.float64)

# set the field to some arbitrary expression
for j in range(args.src_nj):
	for i in range(args.src_ni):
		srcData[j, i] = numpy.sin(2*numpy.pi*srcLons[i]/180.)*numpy.cos(numpy.pi*srcLats[j]/180.)

for j in range(args.dst_nj):
	for i in range(args.dst_ni):
		dstData[j, i] = numpy.sin(2*numpy.pi*dstLons[i]/180.)*numpy.cos(numpy.pi*dstLats[j]/180.)

srcLatCoord = iris.coords.DimCoord(srcLats, standard_name='latitude', units='degrees_north')
srcLonCoord = iris.coords.DimCoord(srcLons, standard_name='longitude', units='degrees_east')
srcCube = iris.cube.Cube(srcData, standard_name='air_temperature', cell_methods=None)
srcCube.add_dim_coord(srcLatCoord, data_dim=0)
srcCube.add_dim_coord(srcLonCoord, data_dim=1)

dstLatCoord = iris.coords.DimCoord(dstLats, standard_name='latitude', units='degrees_north')
dstLonCoord = iris.coords.DimCoord(dstLons, standard_name='longitude', units='degrees_east')
dstCube = iris.cube.Cube(dstData, standard_name='air_temperature', cell_methods=None)
dstCube.add_dim_coord(dstLatCoord, data_dim=0)
dstCube.add_dim_coord(dstLonCoord, data_dim=1)


# save the result
iris.save(srcCube, args.src_file)
iris.save(dstCube, args.dst_file)