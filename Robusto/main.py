from coopr.pyomo import *
from coopr.opt import SolverFactory

from ReferenceModel import _model as model
import cStringIO
import sys
import exporter
import os

#  - - - - - - LEER RUTAS DE DATOS Y RESULTADOS  - - - - - - #

config_rutas = open('config_rutas.txt', 'r')
path_datos = ''
path_resultados = ''
tmp_line = ''

for line in config_rutas:

    if tmp_line == '[datos]':
        path_datos = line.split()[0]
    elif tmp_line == '[resultados]':
        path_resultados = line.split()[0]

    tmp_line = line.split()[0]

if not os.path.exists(path_resultados):
    print "el directorio output: " + path_resultados + " no existe, creando..."
    os.mkdir(path_resultados)

#  - - - - - - CARGAR DATOS AL MODELO  - - - - - - ##

print ("--- Leyendo data ---")
print ("path input:" + path_datos)

data = DataPortal()

data.load(filename=path_datos+'data_gen_static.csv',
          param=(model.gen_barra, model.gen_pmax, model.gen_pmin, model.gen_falla,
                 model.gen_cfijo, model.gen_tipo),
          index=model.GENERADORES)

data.load(filename=path_datos+'data_gen_dyn.csv',
          param=(model.gen_cvar, model.gen_rupmax, model.gen_rdnmax, model.gen_factorcap),
          index=(model.GENERADORES, model.ESCENARIOS))

data.load(filename=path_datos+'data_gen_despachos.csv',
          param=(model.gen_d_uc, model.gen_d_pg, model.gen_d_resup, model.gen_d_resdn),
          index=(model.GENERADORES, model.ESCENARIOS))

data.load(filename=path_datos+'data_lin.csv',
          param=(model.linea_fmax, model.linea_barA, model.linea_barB, model.linea_available, model.linea_x,
                 model.linea_falla),
          index=model.LINEAS)

data.load(filename=path_datos+'data_bar_static.csv',
          param=(model.zona, model.vecinos),
          index=model.BARRAS)

data.load(filename=path_datos+'data_bar_dyn.csv',
          param=model.demanda,
          index=(model.BARRAS, model.ESCENARIOS))

data.load(filename=path_datos+'data_zone.csv',
          param=(model.zonal_rup, model.zonal_rdn),
          index=model.ZONAS)

data.load(filename=path_datos+'data_config.csv',
          param=model.config_value,
          index=model.CONFIG)

data.load(filename=path_datos+'data_scenarios.csv',
          set=model.ESCENARIOS)

print ("--- Creando Modelo ---")
instance = model.create(data)
opt = SolverFactory("cplex")

####  - - - - - - RESOLVIENDO LA OPTIMIZACION  - - - - - - #######
print ("--- Resolviendo la optimizacion ---")
results = opt.solve(instance, tee=True)
# results.write()
instance.load(results)

####  - - - - - - IMPRIMIENDO SI ES NECESARIO  - - - - - - #######

if instance.config_value['debugging']:
    print ("--- Exportando LP ---")
    stdout_ = sys.stdout  # Keep track of the previous value.
    stream = cStringIO.StringIO()
    sys.stdout = stream
    print instance.pprint()  # Here you can do whatever you want, import module1, call test
    sys.stdout = stdout_  # restore the previous stdout.
    variable = stream.getvalue()  # This will get the "hello" string inside the variable

    output = open(path_resultados+'modelo.txt', 'w')
    output.write(variable)
    instance.write(filename=path_resultados+'LP.txt', io_options={'symbolic_solver_labels': True})
    # sys.stdout.write(instance.pprint())
    output.close()

print ('\n--------M O D E L O :  "%s"  T E R M I N A D O --------' % instance.config_value['scuc'])
print ("path input:" + path_datos + '\n')

# ------R E S U L T A D O S------------------------------------------------------------------------------
print ('------E S C R I B I E N D O --- R E S U L T A D O S------\n')

# Resultados para GENERADORES ---------------------------------------------------
exporter.exportar_gen(instance, path_resultados)
# Resultados para LINEAS --------------------------------------------------------
exporter.exportar_lin(instance, path_resultados)
# Resultados para BARRAS (ENS)---------------------------------------------------
exporter.exportar_bar(instance, path_resultados)
# Resultados del sistema --------------------------------------------------------
exporter.exportar_system(instance, path_resultados)
# Resultados de zonas -----------------------------------------------------------
exporter.exportar_zones(instance, path_resultados)







