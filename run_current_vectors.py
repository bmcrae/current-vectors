import sys, time, string, os, math, re
import traceback
from sys import path
from string import split
from current_vectors import *

logFilePath = None

try:
    # settings are for this script, as opposed to options which are for vector script.
    settings = {}
    arrowOptions = {}
    
    ####### USER SETTINGS ##############################
    if len(sys.argv) < 2: #Manual inputs
        arrowOptions['configFile'] = 'C:\\Program Files\\Circuitscape\\examples\\output\\eight_neighbor_example.ini'
        arrowOptions['voltMapFile'] = 'C:\\Program Files\\Circuitscape\\examples\\output\\eight_neighbor_example_voltmap_1_2.asc'       
        arrowOptions['outDir'] = 'c:\\temp2'
        arrowOptions['writeTotalCurrent'] = True # Write total current leaving each pixel
        arrowOptions['writeResultant'] = True # Write vector magnitudes (will be less than total current)
        arrowOptions['writeAllDirections'] = True # Write current leaving pixels from N, NE, E, etc..
        arrowOptions['deleteTempFiles'] = True # Delete everything except standard current map (saved for debug)
        arrowOptions['writeArcVectors'] = True    
    ####################################################
        
    else:
        arrowOptions['configFile'] = sys.argv[1]
        arrowOptions['voltMapFile'] = sys.argv[2]
        arrowOptions['outDir'] = sys.argv[3]
        arrowOptions['writeTotalCurrent']  = sys.argv[4]
        arrowOptions['writeResultant']  = sys.argv[5]
        arrowOptions['writeAllDirections']  = sys.argv[6]
        arrowOptions['writeArcVectors']  = sys.argv[7]
        arrowOptions['deleteTempFiles']  = sys.argv[8]        
    
    startTime=time.clock()

    # Map vectors
    map_current_vectors(arrowOptions) 

except:
    exit_with_python_error(logFilePath,'run_current_vectors.py')
        
        