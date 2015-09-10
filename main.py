from coopr.pyomo import *
#from pyomo.environ import *
from coopr.opt import SolverFactory
#from pyomo.opt import SolverFactory

from ReferenceModel import model
import csv
import cStringIO
import sys

__author__ = 'MPro'
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

data.load(filename=path_datos+'data_gen.tab',
          param=(model.gen_barra, model.gen_pmax, model.gen_pmin, model.gen_cvar, model.gen_falla),
          index=model.GENERADORES)

data.load(filename=path_datos+'data_lin.tab',
          param=(model.linea_fmax, model.linea_barA, model.linea_barB, model.linea_available, model.linea_x), index=model.LINEAS)

data.load(filename=path_datos+'data_bar.tab',
          param=model.demanda,
          index=model.BARRAS)
data.load(filename=path_datos+'data_config.tab',
          param=model.config_value,
          index=model.CONFIG)

# model.pprint()

instance = model.create(data)

opt = SolverFactory("cplex")

####  - - - - - - RESOLVIENDO LA OPTIMIZACION  - - - - - - #######
results = opt.solve(instance)
#results.write()
instance.load(results)

####  - - - - - - IMPRIMIENDO SI ES NECESARIO  - - - - - - #######

if instance.config_value['debugging']:
    stdout_ = sys.stdout  #Keep track of the previous value.
    stream = cStringIO.StringIO()
    sys.stdout = stream
    print instance.pprint()  # Here you can do whatever you want, import module1, call test
    sys.stdout = stdout_  # restore the previous stdout.
    variable = stream.getvalue()  # This will get the "hello" string inside the variable

    output = open(path_resultados+'modelo.txt', 'w')
    output.write(variable)
    instance.write(filename=path_resultados+'LP.txt',io_options={'symbolic_solver_labels':True})
    #sys.stdout.write(instance.pprint())
    output.close()


# ------R E S U L T A D O S------------------------------------------------------------------------------
# resultados para GENERADORES---------------------------------------------------------
ofile  = open(path_resultados+'resultados_generadores.csv', "wb")
writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
gen = instance.GENERADORES
scen = instance.SCENARIOS_FALLA_GX

varpg = getattr(instance, str('GEN_PG'))
varuc = getattr(instance, str('GEN_UC'))
varpg_s = getattr(instance, str('GEN_PG_S'))
tmprow = []
#header
header = ['Generador','UC','PG_0']
for s in scen:
    header.append(str(s))
writer.writerow(header)

for g in gen:
    tmprow.append(g)
    tmprow.append(str(varuc[g].value))
    tmprow.append(str(varpg[g].value))

    for s in scen:
        tmprow.append(str(varpg_s[g,s].value))
    writer.writerow(tmprow)
    tmprow = []

# resultados para LINEAS---------------------------------------------------------