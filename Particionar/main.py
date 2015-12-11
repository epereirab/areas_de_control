from coopr.pyomo import *
from coopr.opt import SolverFactory

from MasterModel import _model as master_model
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
          param=(master_model.gen_barra, master_model.gen_pmax, master_model.gen_pmin, master_model.gen_falla,
                 master_model.gen_cfijo, master_model.gen_tipo),
          index=master_model.GENERADORES)

data.load(filename=path_datos+'data_gen_dyn.csv',
          param=(master_model.gen_cvar, master_model.gen_rupmax, master_model.gen_rdnmax, master_model.gen_factorcap),
          index=(master_model.GENERADORES, master_model.ESCENARIOS))

data.load(filename=path_datos+'data_gen_despachos.csv',
          param=(master_model.gen_d_uc, master_model.gen_d_pg, master_model.gen_d_resup, master_model.gen_d_resdn),
          index=(master_model.GENERADORES, master_model.ESCENARIOS))

data.load(filename=path_datos+'data_lin.csv',
          param=(master_model.linea_fmax, master_model.linea_barA, master_model.linea_barB,
                 master_model.linea_available, master_model.linea_x, master_model.linea_falla),
          index=master_model.LINEAS)

data.load(filename=path_datos+'data_bar_static.csv',
          param=(master_model.zona, master_model.vecinos),
          index=master_model.BARRAS)

data.load(filename=path_datos+'data_bar_dyn.csv',
          param=master_model.demanda,
          index=(master_model.BARRAS, master_model.ESCENARIOS))

data.load(filename=path_datos+'data_zone.csv',
          param=(master_model.zonal_rup, master_model.zonal_rdn),
          index=master_model.ZONAS)

data.load(filename=path_datos+'data_config.csv',
          param=master_model.config_value,
          index=master_model.CONFIG)

data.load(filename=path_datos+'data_scenarios.csv',
          set=master_model.ESCENARIOS)
data.load(filename=path_datos+'data_scenarios.csv',
          set=master_model.PARTICIONES)

print ("--- Creando Modelo ---")
instance = master_model.create(data)
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







