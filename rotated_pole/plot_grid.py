from matplotlib import pylab
import argparse
import iris
import numpy

iris.FUTURE.netcdf_promote = True


parser = argparse.ArgumentParser(description='Plot grid')
parser.add_argument('--src_file', type=str, dest='src_file', default='src.nc',
                    help='Source data file name')
parser.add_argument('--dst_file', type=str, dest='dst_file', default='dst.nc',
                    help='Destination data file name')

args = parser.parse_args()

pylab.figure()

def plotCellAreas(cube):
	coords = cube.coords()
	lats = coords[0].points
	lons = coords[1].points
	dlats = lats[1:, :] - lats[:-1, :]
	dlons = lons[:, 1:] - lons[:, :-1]
	dlatMid = 0.5*(dlats[:, :-1] + dlats[:, 1:])
	dlonMid = 0.5*(dlons[:-1, :] + dlons[1:, :])
	areas = numpy.zeros(lats.shape, lats.dtype)
	areas[:-1, :-1] = dlatMid * dlonMid
	negativeAreas = numpy.zeros(lats.shape, lats.dtype)
	nlat, nlon = lats.shape
	area_max = 10 * (180./nlat) * (360./nlon)
	negativeAreas[numpy.where(numpy.abs(areas) > area_max)] = 1.0
	pylab.pcolor(lons, lats, negativeAreas, cmap='bone_r')

def plotGrid(cube, lineType='k--'):
	coords = cube.coords()
	lats = coords[0].points
	lons = coords[1].points
	nj, ni = lats.shape
	# number of grid lines
	nc = 20
	njstep, nistep = max(1, nj//nc), max(1, ni//nc)
	for j in range(0, nj, njstep):
		y = lats[j, :]
		x = lons[j, :]
		pylab.plot(x, y, lineType)
	for i in range(0, ni, nistep):
		y = lats[:, i]
		x = lons[:, i]
		pylab.plot(x, y, lineType)


srcCubes = iris.load(args.src_file)
srcCube = None
for cb in srcCubes:
    if cb.var_name == 'pointData':
        srcCube = cb

dstCubes = iris.load(args.dst_file)
dstCube = None
for cb in dstCubes:
    if cb.var_name == 'pointData':
        dstCube = cb

#plotCellAreas(srcCube)
plotGrid(srcCube, 'g-')
plotGrid(dstCube, 'r-')

pylab.show()
