# PROBLEM: Arrows do not display neatly for fine-scaled data.  would need to seriously subsample
# build into pinchpoint mapper? NOT NOW- PROBLEM ABOVE IS BARRIER

# tried MGET- does lines, not easily tweaked
#add option to do flow in OR flow out
#del matrices as soon as unneeded

import sys, time, string, os, math
import ConfigParser
import traceback

import numpy
import shutil

from sys import path
from string import split
from math import sqrt, atan2
from numpy import *

import copy
import subprocess

global gdal_available 
gdal_available = False
print_timings = False

version = '2013_0408'

def print_timing(func):
    def wrapper(*arg):
        print_timings_spaces = 0
        print_timings_spaces +=  2
        t1 = time.time()
        res = func(*arg)
        t2 = time.time()
        print_timings_spaces -=  2
        if print_timings:
            print str(int(1000 * (t2 - t1))) + 'ms: ',
            for i in range(0,print_timings_spaces):
                print" ",
            print'%s' % func.func_name
            sys.stdout.flush()
        return res
    return wrapper

    
def create_log_file(logDir, settings):
    ft = tuple(time.localtime())
    timeNow = time.ctime()
    fileName = ('%s_%s_%s_%s%s_%s.txt' % (ft[0], ft[1], ft[2], ft[3], ft[4], 'range_shift'))
    filePath = os.path.join(logDir,fileName)
    try:
        logFile=open(filePath,'a')
    except:
        logFile=open(filePath,'w')
    logFile.write('*'*70 + '\n')
    logFile.write('Range shift log file\n')
    logFile.write('Start time:\t%s \n' % (timeNow))
    logFile.write('settings: ' + str(settings) + '\n')
    logFile.write('*'*70 + '\n\n')
    logFile.close()
    return filePath    
    

def lprint(logFilePath, string):
    print(string)
    try:
        write_log(logFilePath, string)
    except:
        pass

        
def write_log(logFilePath, string):
    try:
        logFile=open(logFilePath,'a')
    except:
        logFile=open(logFilePath,'w')
    try:
        #Sometimes int objects returned for arc failures so need str below
        logFile.write(str(string) + '\n')
    except IOError:
        pass
    finally:
        logFile.close()


def close_log_file(logFilePath):
    timeNow = time.ctime()
    try:
        logFile.write('\nStop time:\t\t%s \n\n' % (timeNow))
        logFile.close()
    except:
        pass
        
   
@print_timing        
def get_g_connection(cs_options,g_map,g_map_direction):
    numpy.seterr(invalid='ignore')
    numpy.seterr(divide='ignore')
    if cs_options['connect_using_avg_resistances'] == False:
        g_direction= where (g_map == -9999, 0, where(g_map_direction == -9999,0,(g_map_direction+g_map)/2))    
        # g_direction = (g_map_direction+g_map)/2
    else:
        g_direction= where (g_map == -9999, 0, where(g_map_direction == -9999,0, (1 /((1/g_map+1/g_map_direction)/2))))    
        # g_direction = 1 /((1/g_map+1/g_map_direction)/2)
    # g_direction= where (g_map == -9999, 0, where(g_map_direction == -9999,0,g_direction))    

    return g_direction
    
@print_timing            
def get_vdiff(cs_options,voltMap,voltMap_direction):
    vdiff_direction = (voltMap - voltMap_direction)
    vdiff_direction = where (voltMap == -9999, 0, where(voltMap_direction == -9999,0,vdiff_direction))
    vdiff_direction = where (vdiff_direction < 0, 0, vdiff_direction)
    return vdiff_direction
    
   
@print_timing        
def get_horiz_neighbors(map):
    m = map.shape[0]
    n = map.shape[1]
    zeromap = zeros(map.shape,dtype = 'float64') 
    map_l  = zeromap.copy()
    map_r  = zeromap.copy()
    
    map_l[:,1:n] = map[:, 0:(n-1)]
    map_r[:,0:(n-1)] = map[:, 1:n]
    return map_l, map_r

@print_timing        
def get_vert_neighbors(map):
    m = map.shape[0]
    n = map.shape[1]
    zeromap = zeros(map.shape,dtype = 'float64') 
    map_u  = zeromap.copy()
    map_d  = zeromap.copy()

    map_u[1:m, :] = map[0:(m-1), :]
    map_d[0:(m-1) , :] = map[1:m , :]
    
    return map_u, map_d

def get_diag1_neighbors(map):
    m = map.shape[0]
    n = map.shape[1]   
    zeromap = zeros(map.shape,dtype = 'float64') 
    map_ul  = zeromap.copy()
    map_ul[1:m,1:n] = map[0:m-1, 0:n-1]
    map_dr  = zeromap.copy()
    map_dr[0:m-1, 0:n-1  ] = map[1:m , 1:n ]
    return map_ul, map_dr


def get_diag2_neighbors(map):
    m = map.shape[0]
    n = map.shape[1]
    zeromap = zeros(map.shape,dtype = 'float64') 
    map_ur  = zeromap.copy()
    map_ur[1:m,0:n-1] = map[0:m-1, 1:n  ]
    map_dl  = zeromap.copy()
    map_dl[0:m-1, 1:n  ] = map[1:m  , 0:n-1]
    return map_ur, map_dl
    
    
@print_timing        
def read_map(state,filename):
    (ncols, nrows, xllcorner, yllcorner, cellsize, nodata) = read_header(filename)
    state['ncols'] = ncols
    state['nrows'] = nrows
    state['xllcorner'] = xllcorner
    state['yllcorner'] = yllcorner
    state['cellsize'] = cellsize
    if nodata==False:
        state['nodata'] = -9999
    else:
        state['nodata'] = nodata
    
    map = reader(filename, 'float64')
    return state, map
    
    
@print_timing        
def read_hab_map(state, cs_options, filename):
    (ncols, nrows, xllcorner, yllcorner, cellsize, nodata) = read_header(filename)
    state['ncols'] = ncols
    state['nrows'] = nrows
    state['xllcorner'] = xllcorner
    state['yllcorner'] = yllcorner
    state['cellsize'] = cellsize
    if nodata==False:
        state['nodata'] = -9999
    else:
        state['nodata'] = nodata

    cell_map = reader(filename, 'float64')   
   
    if cs_options['habitat_map_is_resistances'] == True:
        zeros_in_resistance_map = (where(cell_map==0, 1, 0)).sum() > 0
        if zeros_in_resistance_map == True: 
            raise RuntimeError('Error: zero resistance values are not currently supported for habitat maps.  Use a short-circuit region file instead.')
        g_map = 1 / cell_map  
        g_map = where(cell_map == -9999,0,g_map)
    else:
        g_map = where(cell_map == -9999,0,cell_map)    
    g_map = where(g_map < 0,0,g_map)    
    return state, g_map
    
    
def read_header(filename):
    if os.path.isfile(filename)==False:
        raise RuntimeError('File "'  + filename + '" does not exist')
    fileBase, fileExtension = os.path.splitext(filename) 
    if fileExtension == '.npy': #numpy array will have an associated header file
        filename = fileBase + '.hdr'

    f = open(filename, 'r')
    try:
        [ign, ncols] = string.split(f.readline())
    except ValueError:
            raise  RuntimeError('Unable to read ASCII grid: "'  + filename + '". If file is a text list, please use .txt extension.')
    ncols = int(ncols)
    [ign, nrows] = string.split(f.readline())
    nrows = int(nrows)
    [ign, xllcorner] = string.split(f.readline())
    xllcorner = float(xllcorner)
    [ign, yllcorner] = string.split(f.readline())
    yllcorner = float(yllcorner)
    [ign, cellsize] = string.split(f.readline())
    cellsize = float(cellsize)

    try:
        [ign, nodata] = string.split(f.readline())
        try:
            nodata= int(nodata)
        except ValueError:
            nodata= float(nodata)
    except ValueError:
        nodata=False

    f.close()

    return ncols, nrows, xllcorner, yllcorner, cellsize, nodata 

@print_timing        
def reader(filename, type):
    if os.path.isfile(filename)==False:      
        raise RuntimeError('File "'  + filename + '" does not exist')
    (ncols, nrows, xllcorner, yllcorner, cellsize, nodata) = read_header(filename)

    fileBase, fileExtension = os.path.splitext(filename)     
    if fileExtension == '.npy': 
        map = numpy.load(filename, mmap_mode=None)
        map = map.astype('float64')
            
    else:
        if nodata==False:
            map = loadtxt(filename, skiprows=5, dtype=type)
        else:
            map = loadtxt(filename, skiprows=6, dtype=type)
            map = where(map==nodata, -9999, map)

    if nrows==1:
        temp=numpy.zeros((1,map.size))
        temp[0,:]=map
        map=temp
    if ncols==1:
        temp=numpy.zeros((map.size,1))
        temp[:,0]=map
        map=temp       

    return map

@print_timing        
def writer(file, data, state, compress, projectionFile):    
    #outputDir, outputFile = os.path.split(file)
    outputBase, outputExtension = os.path.splitext(file) 
    if projectionFile is not None:
        try:
            shutil.copyfile(projectionFile,outputBase+'.prj')
        except:
            pass
    if outputExtension == '.npy': #read numpy array, so write one.
        numpy.save(file, data)
        return
    if gdal_available == True:
        format = "MEM"
        driver = gdal.GetDriverByName( format )      
        dst_ds = driver.Create( file, len(data[0]), len(data),1,gdal.GDT_Float32)

        ull=state['yllcorner']+(state['cellsize'])*(len(data))
        dst_ds.SetGeoTransform([state['xllcorner'],  # left x
                             state['cellsize'],   # w-e pixel resolution
                             0,                   # rotation
                             ull,                 # upper left corner y
                             0,                   # rotation
                             state['cellsize']])   # n-s pixel resolution
                             

        dst_ds.GetRasterBand(1).WriteArray(data)
        format = 'AAIGrid'
        driver = gdal.GetDriverByName(format)
        dst_ds_new = driver.CreateCopy(file, dst_ds) #STILL GETTING LEADING SPACES.
        dst_ds = None
        
    else:
        f = False
        if compress == True:
            file = file + '.gz'
            f = gzip.open(file, 'w')
        else:
            f = open(file, 'w')
        f.write('ncols         ' + str(state['ncols']) + '\n')
        f.write('nrows         ' + str(state['nrows']) + '\n')
        f.write('xllcorner     ' + str(state['xllcorner']) + '\n')
        f.write('yllcorner     ' + str(state['yllcorner']) + '\n')
        f.write('cellsize      ' + str(state['cellsize']) + '\n')
        f.write('NODATA_value  ' + str(state['nodata']) + '\n')
        
        delimiter = ''
        fmt = ['%.6f ']*state['ncols'] 
        format = delimiter.join(fmt)
        for row in data:
            f.write(format % tuple(row) + '\n')

        f.close()
    

def delete_col(A, delcol):
    """Deletes columns from a matrix

    From gapdt.py by Viral Shah

    """
    m = A.shape[0]
    n = A.shape[1]
    keeprows = arange(0, m)
    keepcols = delete(arange(0, n), delcol)
    return A[keeprows][:, keepcols]
    

def delete_row(A, delrow):
    """Deletes rows from a matrix

    From gapdt.py by Viral Shah

    """
    m = A.shape[0]
    n = A.shape[1]
    keeprows = delete(arange(0, m), delrow)
    keepcols = arange(0, n)
    return A[keeprows][:, keepcols]

    
def readConfigFile(configFile):

    if os.path.isfile(configFile)==False:
        raise RuntimeError('File "'  + configFile + '" does not exist')

    config = ConfigParser.ConfigParser()
    config.read(configFile)
    cs_options={}
    
    cs_options['set_null_voltages_to_nodata']=True 
    cs_options['set_null_currents_to_nodata']=True 
    cs_options['set_focal_node_currents_to_zero']=False
    cs_options['write_max_cur_maps']=False 
    cs_options['low_memory_mode']=False        
    cs_options['use_mask']=False
    cs_options['mask_file']='None' 
    cs_options['use_included_pairs']=False
    cs_options['included_pairs_file']='None' 
    cs_options['use_variable_source_strengths']=False
    cs_options['variable_source_file']='None' 
    cs_options['data_type']='raster' 
    cs_options['version']='unknown'
        
    for section in config.sections():
        for option in config.options(section):
            try:
                cs_options[option]=config.getboolean(section, option)
            except:
                cs_options[option]=config.get(section, option)
    return cs_options

def writeConfigFile(configFile, cs_options):
   
    config = ConfigParser.ConfigParser()
 
    sections={}
    section='Version'
    sections['version']=section
    
    section='Connection scheme for raster habitat data'
    sections['connect_four_neighbors_only']=section
    sections['connect_using_avg_resistances']=section
    
    section='Short circuit regions (aka polygons)'
    sections['use_polygons']=section
    sections['polygon_file']=section
    
    section='cs_options for advanced mode'
    sections['source_file']=section
    sections['ground_file']=section
    sections['ground_file_is_resistances']=section
    sections['use_unit_currents']=section
    sections['use_direct_grounds']=section
    sections['remove_src_or_gnd']=section
    
    section='Calculation cs_options'
    sections['solver']=section
    sections['print_timings']=section
    sections['low_memory_mode']=section    
    
    section='Output cs_options'
    sections['output_file']=section
    sections['write_cur_maps']=section
    sections['write_cum_cur_map_only']=section
    sections['write_max_cur_maps']=section
    sections['log_transform_maps']=section
    sections['write_volt_maps']=section
    sections['compress_grids']=section
    sections['set_null_voltages_to_nodata']=section
    sections['set_null_currents_to_nodata']=section
    sections['set_focal_node_currents_to_zero']=section
    
    section='Mask file'
    sections['use_mask']=section
    sections['mask_file']=section  
    
    section='cs_options for pairwise and one-to-all and all-to-one modes'
    sections['use_included_pairs']=section
    sections['included_pairs_file']=section
    sections['point_file']=section
    sections['point_file_contains_polygons']=section
    
    section='cs_options for one-to-all and all-to-one modes'
    sections['use_variable_source_strengths']=section
    sections['variable_source_file']=section

    
    section='Habitat raster or graph'
    sections['habitat_file']=section
    sections['habitat_map_is_resistances']=section
    
    section="Circuitscape mode"
    sections['scenario']=section
    sections['data_type']=section

    if cs_options['ground_file_is_resistances']=='not entered':
        cs_options['ground_file_is_resistances'] = False
    if cs_options['point_file_contains_polygons']=='not entered':
        cs_options['point_file_contains_polygons'] = False
 
    for option in sections:
        try:
            config.add_section(sections[option])
        except:
            pass
    for option in sections:
        config.set(sections[option], option, cs_options[option])

    f = open(configFile, 'w')
    config.write(f)
    f.close()
 


def set_default_cs_options():
    cs_options = {}
    cs_options['data_type']='raster' 
    cs_options['version']='unknown'
    cs_options['low_memory_mode']=False
    cs_options['scenario']='advanced'
    
    cs_options['habitat_map_is_resistances']=True
    cs_options['point_file']='(Browse for file with locations of focal points or areas)'
    cs_options['point_file_contains_polygons']=False
    cs_options['connect_four_neighbors_only']=False
    cs_options['connect_using_avg_resistances']=True
    cs_options['use_polygons']=False
    cs_options['polygon_file']='(Browse for a short-circuit region file)'
    cs_options['ground_file_is_resistances']=True
    cs_options['use_unit_currents']=False
    cs_options['use_direct_grounds']=True
    cs_options['remove_src_or_gnd']='not entered'
    cs_options['write_cur_maps']=False # Set to true to write standard current maps
    cs_options['write_cum_cur_map_only']=False
    cs_options['log_transform_maps']=False
    cs_options['write_volt_maps']=True
    cs_options['solver']='cg+amg'
    cs_options['compress_grids']=False
    cs_options['print_timings']=False
    cs_options['use_mask']=False
    cs_options['mask_file']='None' 
    cs_options['use_included_pairs']=False
    cs_options['included_pairs_file']='None' 
    cs_options['use_variable_source_strengths']=False
    cs_options['variable_source_file']='None' 
    cs_options['set_null_voltages_to_nodata']=True # Default must be false or re-do verify .ini files
    cs_options['set_null_currents_to_nodata']=True # Default must be false or re-do verify .ini files
    cs_options['write_max_cur_maps']=False
    cs_options['set_focal_node_currents_to_zero']=False
    
    return cs_options
   
   
def get_cs_path(circuitscapeDir):
    """Returns path to Circuitscape installation """
    csPath = os.path.join(circuitscapeDir,'Circuitscape\\cs_run.exe')
    if os.path.exists(csPath): 
        return csPath
    envList = ["ProgramW6432", "ProgramFiles", "ProgramFiles(x86)"]
    for x in range (0,len(envList)):
        try:
            pfPath = os.environ[envList[x]]
            csPath = os.path.join(pfPath,'Circuitscape\\cs_run.exe')
            if os.path.exists(csPath): return csPath
        except: pass
    return None

    
def call_circuitscape(CSPATH, outConfigFile, logFilePath):
    memFlag = False
    failFlag = False
    solverFailure = False
    lprint(logFilePath, '     Calling Circuitscape:')
    proc = subprocess.Popen([CSPATH, outConfigFile],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                           shell=True)
    while proc.poll() is None:
        output = proc.stdout.readline()

        if 'Traceback' in output:
            lprint(logFilePath, "\nCircuitscape failed.")
            failFlag = True
            if 'memory' in output:
                memFlag = True
        elif 'failed' in output:
            solverFailure = True
        if ('Processing' not in output and 'laplacian' not in output and 
                'node_map' not in output and (('--' in output) or 
                ('sec' in output) or (failFlag == True))):
            lprint(logFilePath, "      " + output.replace("\r\n",""))                

    # Catch any output lost if process closes too quickly
    output=proc.communicate()[0]
    for line in output.split('\r\n'):
        if 'Traceback' in line:
            lprint(logFilePath, "\nCircuitscape failed.")
            if 'memory' in line:
                memFlag = True
        if ('Processing' not in line and 'laplacian' not in line and 
                'node_map' not in line and (('--' in line) or 
                ('sec' in line) or (failFlag == True))):
           lprint(logFilePath, "      " + str(line))#.replace("\r\n","")))              
    return memFlag, failFlag, solverFailure


def exit_with_python_error(logFilePath,filename):
    """Handle python errors and provide details to user"""
    tb = sys.exc_info()[2]  # get the traceback object
    # tbinfo contains the error's line number and the code
    tbinfo = traceback.format_tb(tb)[0]
    line = tbinfo.split(", ")[1]

    err = traceback.format_exc().splitlines()[-1]
    lprint(logFilePath,'\n\n*************************************')
    msg = ("Python error on **" + line + "** of " + filename + ":")
    lprint(logFilePath,msg)
    lprint(logFilePath,err)
    if logFilePath is not None:
        close_log_file(logFilePath)
    raw_input('Press any key to continue')
    exit(1)

    
def elapsed_time(logFilePath, start_time):
    """Returns elapsed time given a start time"""
    now = time.clock()
    elapsed = now - start_time
    secs = (float(int(elapsed*100)))/100
    mins = int(elapsed / 60)
    hours = int(mins / 60)
    mins = mins - hours * 60
    secs = secs - mins * 60 - hours * 3600
    if mins == 0:
        lprint(logFilePath,'That took ' + str(secs) + ' seconds.\n')
    elif hours == 0:
        lprint(logFilePath,'That took ' + str(mins) + ' minutes and ' +
                          str(secs) + ' seconds.\n')
    else:
        lprint(logFilePath,'That took ' + str(hours) + ' hours ' +
                          str(mins) + ' minutes and ' + str(secs) +
                          ' seconds.\n')
    return now

    
@print_timing        
def map_current_vectors(arrowOptions):
    try:
        
        outDir = arrowOptions['outDir']
        outBase, dirName = os.path.split(outDir)
        scratchDir = os.path.join(outBase, 'arrowScratch')
        logDir = os.path.join(outBase, 'arrowLog')
        
        print 'Creating directories'
        if not os.path.exists(scratchDir):
            os.mkdir(scratchDir)
        if not os.path.exists(outDir):
            os.makedirs(outDir)
        if not os.path.exists(logDir):
            os.mkdir(logDir)   
        logFilePath = create_log_file(logDir, arrowOptions)    
        lprint(logFilePath, 'Current Vectors Version = ' + version + '\n')    
    
        state = {}
        cs_options = readConfigFile(arrowOptions['configFile'])
        csOutDir, baseOutputFN = os.path.split(arrowOptions['voltMapFile'])
        baseFile, ext = os.path.splitext(baseOutputFN)
        baseOutputFile = os.path.join(outDir,baseFile)
        baseOutputFile = baseOutputFile.replace('voltmap','vector')
        state,voltMap = read_map(state, arrowOptions['voltMapFile'])
        habMapFile = cs_options['habitat_file'] 
        habMapFileBaseFN, ext = os.path.splitext(habMapFile)
        
        projectionFile = habMapFileBaseFN + '.prj'
        if not os.path.exists(projectionFile):
            projectionFile = None
            
        state,g_map = read_hab_map(state, cs_options, habMapFile)
        
        voltMap_ul, voltMap_dr = get_diag1_neighbors(voltMap)
        voltMap_ur, voltMap_dl = get_diag2_neighbors(voltMap)
        voltMap_l, voltMap_r = get_horiz_neighbors(voltMap)
        voltMap_u, voltMap_d = get_vert_neighbors(voltMap)
       
        g_map_ul, g_map_dr = get_diag1_neighbors(g_map)
        g_map_ur, g_map_dl = get_diag2_neighbors(g_map)
        g_map_l, g_map_r = get_horiz_neighbors(g_map)
        g_map_u, g_map_d = get_vert_neighbors(g_map)
 
        g_N = get_g_connection(cs_options,g_map,g_map_u)
        g_S = get_g_connection(cs_options,g_map,g_map_d)
        g_E = get_g_connection(cs_options,g_map,g_map_r)
        g_W = get_g_connection(cs_options,g_map,g_map_l)
        
        if cs_options['connect_four_neighbors_only'] == False:
            g_NE = (get_g_connection(cs_options,g_map,g_map_ur))/sqrt(2) 
            g_SE = (get_g_connection(cs_options,g_map,g_map_dr))/sqrt(2) 
            g_SW = (get_g_connection(cs_options,g_map,g_map_dl))/sqrt(2) 
            g_NW = (get_g_connection(cs_options,g_map,g_map_ul))/sqrt(2) 
        
        vdiff_N = get_vdiff(cs_options,voltMap,voltMap_u)
        vdiff_S = get_vdiff(cs_options,voltMap,voltMap_d)
        vdiff_E = get_vdiff(cs_options,voltMap,voltMap_r)
        vdiff_W = get_vdiff(cs_options,voltMap,voltMap_l)
        if cs_options['connect_four_neighbors_only'] == False:
            vdiff_NE = get_vdiff(cs_options,voltMap,voltMap_ur)
            vdiff_SE = get_vdiff(cs_options,voltMap,voltMap_dr)
            vdiff_SW = get_vdiff(cs_options,voltMap,voltMap_dl)
            vdiff_NW = get_vdiff(cs_options,voltMap,voltMap_ul)

        iN = multiply(vdiff_N, g_N)
        iS = multiply(vdiff_S, g_S)
        iE = multiply(vdiff_E, g_E)
        iW = multiply(vdiff_W, g_W)
        del vdiff_N, vdiff_S, vdiff_E, vdiff_W
        if cs_options['connect_four_neighbors_only'] == False:
            iNE = multiply(vdiff_NE, g_NE)
            iSE = multiply(vdiff_SE, g_SE)
            iSW = multiply(vdiff_SW, g_SW)
            iNW = multiply(vdiff_NW, g_NW)
            del vdiff_NE, vdiff_SE, vdiff_NW, vdiff_SW
        iNetN = iN - iS
        iNetE = iE - iW
        if cs_options['connect_four_neighbors_only'] == False:
            iNetNE = iNE - iSW
            iNetSE = iSE - iNW
            iNetN = iNetN + (iNetNE / sqrt(2)) - (iNetSE / sqrt(2))
            iNetE = iNetE + (iNetNE / sqrt(2)) + (iNetSE / sqrt(2))
            del iNetNE
            del iNetSE
        mag = where(voltMap == -9999, -9999, sqrt(square(iNetN) + square(iNetE)))     
        angle = where(voltMap == -9999, -9999, arctan2(iNetN,iNetE))
       
        if arrowOptions['writeTotalCurrent']:
            if cs_options['connect_four_neighbors_only'] == False:
                iTot = iN + iS + iE + iW + iNE + iSE + iSW + iNW
            else:
                iTot = iN + iS + iE + iW 
            iTot = where(voltMap == -9999, -9999, iTot)
            angle = where(iTot == 0, -9999, angle)
            writer(baseOutputFile+'_grossMagnitude.asc', iTot, state, False, projectionFile)
        del voltMap        
        
        writer(baseOutputFile+'_angle.asc', angle, state, False, projectionFile)
        
        if arrowOptions['writeResultant']:
            writer(baseOutputFile+'_magnitude.asc', mag, state, False, projectionFile)

        if arrowOptions['writeAllDirections']:
            writer(baseOutputFile+'_iN.asc', iN, state, False, projectionFile)
            writer(baseOutputFile+'_iS.asc', iS, state, False, projectionFile)
            writer(baseOutputFile+'_iE.asc', iE, state, False, projectionFile)
            writer(baseOutputFile+'_iW.asc', iW, state, False, projectionFile)
            del iN, iS, iE, iW
            if cs_options['connect_four_neighbors_only'] == False:
                writer(baseOutputFile+'_iNE.asc', iNE, state, False, projectionFile)
                writer(baseOutputFile+'_iSE.asc', iSE, state, False, projectionFile)
                writer(baseOutputFile+'_iSW.asc', iSW, state, False, projectionFile)
                writer(baseOutputFile+'_iNW.asc', iNW, state, False, projectionFile)
                del iNE, iSE, iSW, iNW
            writer(baseOutputFile+'_iNetN.asc', iNetN, state, False, projectionFile)
            writer(baseOutputFile+'_iNetE.asc', iNetE, state, False, projectionFile)

        if arrowOptions['writeArcVectors']:
            try:
                import arcpy
                arcpy.CheckOutExtension("Spatial")
                arcpy.overwriteOutput = True
                arcpy.env.overwriteOutput = True
                
                field = "VALUE"
                # Execute RasterToPoint
                # if arrowOptions['writeTotalCurrent']:
                    # inRaster = baseOutputFile+'_grossMagnitude.asc'
                # else:
                inRaster = baseOutputFile+'_magnitude.asc'
                outPoint = baseOutputFile + '_' + 'arrows.shp'
                if arcpy.Exists(outPoint):
                    arcpy.Delete_management(outPoint)
                startTime=time.clock()
                
                arcpy.RasterToPoint_conversion(inRaster, outPoint, field)

                angleRaster = baseOutputFile+'_angle.asc'
                if arrowOptions['writeAllDirections']:
                    if cs_options['connect_four_neighbors_only'] == True:
                        inRasterList = [[angleRaster, "radians"],[baseOutputFile+'_iN.asc',"i_North"],[baseOutputFile+'_iS.asc',"i_South"],[baseOutputFile+'_iE.asc',"i_East"],[baseOutputFile+'_iW.asc',"i_West"]]
                    else:
                        inRasterList = [[angleRaster, "radians"],[baseOutputFile+'_iN.asc',"i_North"],[baseOutputFile+'_iS.asc',"i_South"],[baseOutputFile+'_iE.asc',"i_East"],[baseOutputFile+'_iW.asc',"i_West"],[baseOutputFile+'_iNE.asc',"i_NE"],[baseOutputFile+'_iSE.asc',"i_SE"],[baseOutputFile+'_iSW.asc',"i_SW"],[baseOutputFile+'_iNW.asc',"i_NW"]]
                else:
                    inRasterList = [[angleRaster, "radians"]]
                grossMagRaster = baseOutputFile+'_grossMagnitude.asc'
                if arrowOptions['writeTotalCurrent']:    
                    inRasterList.append([grossMagRaster, "GrossMag"])

                arcpy.sa.ExtractMultiValuesToPoints(outPoint, inRasterList, "NONE") #faster, allows multi rasters, name of field
                arcpy.AddField_management(outPoint, "Degrees", "DOUBLE")
                if arrowOptions['writeResultant']:
                    arcpy.AddField_management(outPoint, "Mag", "DOUBLE")
                    
                rows = arcpy.UpdateCursor(outPoint)
                for row in rows:
                    radians = row.getValue("radians")
                    row.setValue("Degrees", radians*180/pi)
                    if arrowOptions['writeResultant']:
                        row.setValue("Mag", row.getValue("GRID_CODE"))
                    rows.updateRow(row)
                del row, rows                
                lprint(logFilePath,'\nESRI shapefile with magnitudes and angles written.')  
                lprint(logFilePath,'You can symbolize this using arrow marker symbols in ArcMap ')
                lprint(logFilePath,'with an arithmetic rotation style and rotation of Degrees + 90.')
                
            except arcpy.ExecuteError:        
                msg=arcpy.GetMessages(2)
                print(msg)        
            
    except:
        exit_with_python_error(logFilePath,'curent_vectors.py')
  

    # import pylab
    # ncols = state['ncols']
    # nrows = state['nrows']
    # x, y = meshgrid(arange(0, ncols), arange(0, nrows))
    # u = iNetN*5
    # v = iNetE*5
    # pylab.close('all')
    # pylab.figure()
    # # Q = pylab.quiver( v, u)
    # Q=pylab.quiver(x,y, v, u, angles='xy', scale_units='xy', scale=10)
    # pylab.show()
    # # time.sleep(5)
    # pylab.close('all')
    # # pylab.close('all')
    # # pylab.ion()
    # # pylab.figure(figsize=[8, 8])
    # # pylab.quiver(x, y, u, v, angles='xy', scale_units='xy', scale=10)
    # # # ax = pylab.axes()
    # # # ax.set_aspect(1.)
    
    # # pylab.figure()
    # # Q = pylab.quiver( u, v)
    # # pylab.title('Minimal arguments, no kwargs')
    # # pylab.show()
    
# # # qk = quiverkey(Q, 0.5, 0.92, 2, r'$2 \frac{m}{s}$', labelpos='W',
               # # # fontproperties={'weight': 'bold'})
# # # l,r,b,t = axis()
# # # dx, dy = r-l, t-b
# # # axis([l-0.05*dx, r+0.05*dx, b-0.05*dy, t+0.05*dy])


    
    # # time.sleep(3)
    
# # from pylab import *
# # from numpy import ma

# # X,Y = meshgrid( arange(0,2*pi,.2),arange(0,2*pi,.2) )
# # U = cos(X)
# # V = sin(Y)

# #1
# # figure()
# # Q = quiver( U, V)

# # # qk = quiverkey(Q, 0.5, 0.92, 2, r'$2 \frac{m}{s}$', labelpos='W',
               # # # fontproperties={'weight': 'bold'})
# # # l,r,b,t = axis()
# # # dx, dy = r-l, t-b
# # # axis([l-0.05*dx, r+0.05*dx, b-0.05*dy, t+0.05*dy])

# # title('Minimal arguments, no kwargs')
# # show()