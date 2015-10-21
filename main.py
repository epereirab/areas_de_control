from coopr.pyomo import *
from coopr.opt import SolverFactory

from ReferenceModel import _model as model
import csv
import cStringIO
import sys
import exporter

####  - - - - - - LEER RUTAS DE DATOS Y RESULTADOS  - - - - - - #######

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

####  - - - - - - CARGAR DATOS AL MODELO  - - - - - - #######
data = DataPortal()

data.load(filename=path_datos+'data_gen.csv',
          param=(model.gen_barra, model.gen_pmax, model.gen_pmin, model.gen_cvar, model.gen_falla,
                 model.gen_rupmax, model.gen_rdnmax, model.gen_cfijo, model.gen_factorcap, model.gen_tipo),
          index=model.GENERADORES)

data.load(filename=path_datos+'data_despachos.csv',
          param=(model.UC, model.PG_0, model.RES_UP, model.RES_DN),
          index=model.GENERADORES)


data.load(filename=path_datos+'data_lin.csv',
          param=(model.linea_fmax, model.linea_barA, model.linea_barB, model.linea_available, model.linea_x,
                 model.linea_falla),
          index=model.LINEAS)

data.load(filename=path_datos+'data_bar.csv',
          param=(model.demanda, model.zona, model.vecinos),
          index=model.BARRAS)

data.load(filename=path_datos+'data_zone.csv',
          param=(model.zonal_rup, model.zonal_rdn),
          index=model.ZONAS)

data.load(filename=path_datos+'data_config.csv',
          param=model.config_value,
          index=model.CONFIG)

instance = model.create(data)
opt = SolverFactory("cplex")

####  - - - - - - RESOLVIENDO LA OPTIMIZACION  - - - - - - #######
results = opt.solve(instance, tee=True)
# results.write()
instance.load(results)

####  - - - - - - IMPRIMIENDO SI ES NECESARIO  - - - - - - #######

if instance.config_value['debugging']:
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

print ('\n------M O D E L O :  "%s"  T E R M I N A D O------\n' % instance.config_value['scuc'])
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

'''
gen = instance.GENERADORES
scen = instance.CONTINGENCIAS
lin = instance.LINEAS
bar = instance.BARRAS

# Costo total del sistema



def costo_ENS():
    return sum(instance.ENS[b].value * instance.config_value['voll'] for b in instance.BARRAS)

def costo_ENS_escenario(sc):
    return sum(instance.ENS_S[b, sc].value * instance.config_value['voll'] for b in instance.BARRAS)

def costo_op():
    return sum(instance.GEN_PG[g].value * instance.gen_cvar[g] for g in instance.GENERADORES)

def costo_op_escenario(sc):
    return sum(instance.GEN_PG_S[g, sc].value * instance.gen_cvar[g] for g in instance.GENERADORES)

def costo_base():
    return costo_op() + costo_ENS()

def costo_escenario(sc):
    return costo_op_escenario(sc) + costo_ENS_escenario(sc)


# Resultados del Sistema (ENS)---------------------------------------------------------



# RESULTADOS POR AREA ---------------------------------------------------------------------------------------




'''
