from coopr.pyomo import *
#from pyomo.environ import *
from coopr.opt import SolverFactory
#from pyomo.opt import SolverFactory

from ReferenceModel import _model as model
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

data.load(filename=path_datos+'data_gen.csv',
          param=(model.gen_barra, model.gen_pmax, model.gen_pmin, model.gen_cvar, model.gen_falla,
                 model.gen_rupmax, model.gen_rdnmax, model.gen_cfijo, model.gen_factorcap, model.gen_tipo),
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
gen = instance.GENERADORES
scen = instance.CONTINGENCIAS
lin = instance.LINEAS
bar = instance.BARRAS

# Resultados para GENERADORES---------------------------------------------------------
ofile = open(path_resultados + 'resultados_generadores.csv', "wb")
writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

ofile2 = open(path_resultados + 'resultados_generadores_delta.csv', "wb")
writer2 = csv.writer(ofile2, delimiter=',', quoting=csv.QUOTE_NONE)

tmprow = []
tmprow2 = []
# header
header = ['Generador', 'barra', 'zona', 'tipo', 'Cvar', 'Pmax', 'Pmax_eff', 'Pmin', 'UC', 'PG_0', 'RES_UP', 'RES_DN']
for s in scen:
    header.append(str(s))
writer.writerow(header)
writer2.writerow(header)

for g in gen:
    tmprow.append(g)
    tmprow.append(instance.gen_barra[g])
    tmprow.append(instance.zona[instance.gen_barra[g]])
    tmprow.append(instance.gen_tipo[g])
    tmprow.append(instance.gen_cvar[g])
    tmprow.append(instance.gen_pmax[g])
    tmprow.append(instance.gen_pmax[g] * instance.gen_factorcap[g])
    tmprow.append(instance.gen_pmin[g])
    tmprow.append(instance.GEN_UC[g].value)
    tmprow.append(instance.GEN_PG[g].value)
    tmprow.append(instance.GEN_RESUP[g].value)
    tmprow.append(instance.GEN_RESDN[g].value)
    tmprow2 = list(tmprow)
    for s in scen:
        tmprow.append(instance.GEN_PG_S[g, s].value)
        if s == g:
            tmprow2.append('0')

        else:
            tmprow2.append(instance.GEN_PG_S[g, s].value-instance.GEN_PG[g].value)

    writer.writerow(tmprow)
    writer2.writerow(tmprow2)
    tmprow = []
    tmprow2 = []
ofile.close()
ofile2.close()

# Resultados para LINEAS---------------------------------------------------------
ofile = open(path_resultados + 'resultados_lineas.csv', "wb")
writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

tmprow = []
# header
header = ['Linea', 'Flujo_MAX', 'Flujo_0']
for s in scen:
    header.append(str(s))
writer.writerow(header)

for l in lin:
    tmprow.append(l)
    tmprow.append(instance.linea_fmax[l])
    tmprow.append(instance.LIN_FLUJO[l].value)

    for s in scen:
        tmprow.append(instance.LIN_FLUJO_S[l, s].value)
    writer.writerow(tmprow)
    tmprow = []

ofile.close()

# Resultados para BARRAS (ENS)---------------------------------------------------------
ofile = open(path_resultados + 'resultados_barras.csv', "wb")
writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

tmprow = []
# header
header = ['Linea', 'ENS_0']
for s in scen:
    header.append('ENS_' + str(s))
writer.writerow(header)

for b in bar:
    tmprow.append(b)
    tmprow.append(instance.ENS[b].value)

    for s in scen:
        tmprow.append(instance.ENS_S[b, s].value)
    writer.writerow(tmprow)
    tmprow = []

ofile.close()
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

ofile = open(path_resultados + 'resultados_system.csv', "wb")
writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

tmprow = []
# header
header = ['Valor', '0']
for s in scen:
    header.append(str(s))
writer.writerow(header)

tmprow.append('CostoTotal')
tmprow.append(costo_base())
for s in scen:
    tmprow.append(costo_escenario(s))
writer.writerow(tmprow)
tmprow = []

tmprow.append('CostoOperacion')
tmprow.append(costo_op())
for s in scen:
    tmprow.append(costo_op_escenario(s))
writer.writerow(tmprow)
tmprow = []

tmprow.append('CostoENS')
tmprow.append(costo_ENS())
for s in scen:
    tmprow.append(costo_ENS_escenario(s))
writer.writerow(tmprow)
tmprow = []

ofile.close()




