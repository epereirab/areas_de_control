from coopr.pyomo import *
from coopr.opt import SolverFactory

from Master_DEconRR import _model as master_model
from SlaveModel import _model as slave_model
import cStringIO
import sys
# import exporter
import os

#  - - - - - - LEER RUTAS DE DATOS Y RESULTADOS  - - - - - - #

config_rutas = open('config_rutas.txt', 'r')
path_datos = ''
path_resultados = ''
tmp_line = ''

# for line in config_rutas:
#
#     if tmp_line == '[datos]':
#         path_datos = line.split()[0]
#     elif tmp_line == '[resultados]':
#         path_resultados = line.split()[0]
#
#     tmp_line = line.split()[0]
#
# if not os.path.exists(path_resultados):
#     print "el directorio output: " + path_resultados + " no existe, creando..."
#     os.mkdir(path_resultados)

#  - - - - - - CARGAR DATOS AL MODELO  - - - - - - ##

print ("--- Leyendo data ---")

data_master = DataPortal()

path_datos = 'Data/completo/'

print ("path input:" + path_datos)

data_master.load(filename=path_datos+'data_gen_static.csv',
                 param=(master_model.gen_barra, master_model.gen_pmax, master_model.gen_pmin, master_model.gen_falla,
                        master_model.gen_cfijo, master_model.gen_tipo),
                 index=master_model.GENERADORES)

data_master.load(filename=path_datos+'data_gen_dyn.csv',
                 param=(master_model.gen_cvar, master_model.gen_rupmax, master_model.gen_rdnmax, master_model.gen_factorcap),
                 index=(master_model.GENERADORES, master_model.ESCENARIOS))


data_master.load(filename=path_datos+'data_lin.csv',
                 param=(master_model.linea_fmax, master_model.linea_barA, master_model.linea_barB,
                        master_model.linea_available, master_model.linea_x, master_model.linea_falla),
                 index=master_model.LINEAS)

data_master.load(filename=path_datos+'data_bar_static.csv',
                 param=master_model.vecinos,
                 index=master_model.BARRAS)

data_master.load(filename=path_datos+'data_bar_dyn.csv',
                 param=master_model.demanda,
                 index=(master_model.BARRAS, master_model.ESCENARIOS))

data_master.load(filename=path_datos+'data_scenarios.csv',
                 set=master_model.ESCENARIOS)

data_master.load(filename=path_datos+'data_config_CN-CENTRO.csv',
                 param=master_model.config_value,
                 index=master_model.CONFIG)

data_slave = data_master


print ("--- Creando Master ---")
master_instance1 = master_model.create(data_master)


# master_instance2 = master_model.create(data_master2)

print ("--- Creando Slave---")
slave_instance = slave_model.create(data_slave)

opt = SolverFactory("cplex")


def solve_despacho_y_confiabilidad(master, slave, req1, req2):
    master.Req_Z1 = req1
    master.Req_Z2 = req2
    # master.preprocess()
    results_master = opt.solve(master, tee=False)
    print ("Master Resuelto")
    # results_master.write()
    master.load(results_master)

    # Update of slave dispatch parameters
    for g in master.GENERADORES:
        for s in master.ESCENARIOS:
            slave.gen_d_pg[g, s] = min(master.GEN_PG[g, s].value,
                                       slave.gen_pmax[g] * slave.gen_factorcap[g, s])
            slave.gen_d_resup[g, s] = master.GEN_RESUP[g, s].value

    print 'Updating Slave'
    #slave.preprocess()
    print ("--- Resolviendo la optimizacion del SLAVE---")
    results_slave = opt.solve(slave, tee=False)  # tee=True shows the solver info
    slave.load(results_slave)

    return master.Objective_rule(), slave.Objective_rule()

# Datos para la iteracion

GAP_ENS = 10
eps = 0.1
StartingPoints = {0: (100, 100), 1: (150, 100), 2: (100, 150)}
it = 1
max_it = 10
ENS = {}
fobj = {}
planos = {}

is_opt = 0

#Resolviendo puntos de partida
print '\nSolving Starting Points'

for i in [0, 1, 2]:
    print '\nStarting point', i+1
    [fobj[i], ENS[i]] = solve_despacho_y_confiabilidad(master_instance1, slave_instance,
                                                       StartingPoints[i][0], StartingPoints[i][1])
    print 'ENS del punto ', StartingPoints[i], ' = ', ENS[i], ' [MW]'

v1 = (ENS[it+1]-ENS[it-1],
      StartingPoints[it+1][0]-StartingPoints[it-1][0],
      StartingPoints[it+1][1]-StartingPoints[it-1][1])
v2 = (ENS[it]-ENS[it-1],
      StartingPoints[it][0]-StartingPoints[it-1][0],
      StartingPoints[it][1]-StartingPoints[it-1][1])
vnormal = (v1[1]*v2[2]-v1[2]*v2[1],
           v1[2]*v2[0]-v1[0]*v2[2],
           v1[0]*v2[1]-v1[1]*v2[0])
vnormal = (1, vnormal[1]/vnormal[0], vnormal[2]/vnormal[0])
K = vnormal[0]*ENS[it+1] + vnormal[1]*StartingPoints[it+1][0] + vnormal[2]*StartingPoints[it+1][1]
plano = (vnormal[0] * master_instance1.SLAVE_SECURITY +
         vnormal[1] * master_instance1.REQ_RES_Z1 +
         vnormal[2] * master_instance1.REQ_RES_Z2 -
         K)

master_instance1.CT_fix_req_res_z1.deactivate()
master_instance1.CT_fix_req_res_z2.deactivate()

if vnormal[0] > 0:
    master_instance1.CT_cortes.add(plano >= 0)
    master_instance1.preprocess()
else:
    master_instance1.CT_cortes.add(plano <= 0)
    master_instance1.preprocess()

print plano
planos[0] = plano

while is_opt == False:
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
    print ('\n\nIteracion %i' % it)
    it += 1
    fobj[it+1], ENS[it+1] = solve_despacho_y_confiabilidad(master_instance1, slave_instance, 0, 0)
    StartingPoints[it+1] = (master_instance1.REQ_RES_Z1.value, master_instance1.REQ_RES_Z2.value)

    print ('Requerimiento de reserva zona 1: %r [MW]' % StartingPoints[it+1][0])
    print ('Requerimiento de reserva zona 2: %r [MW]' % StartingPoints[it+1][1])
    print ('ENS esperada (MASTER): %r [MW]' % master_instance1.SLAVE_SECURITY.value)
    print ('ENS de la particion: %r [MW]' % ENS[it+1])
    print ('Costo Operacional del Sistema: %r [k$]' % (fobj[it+1]/1000))

    # TODO: Agregar corte usando los 3 ultimos puntos.
    v1 = (ENS[it+1]-ENS[it-1],
          StartingPoints[it+1][0]-StartingPoints[it-1][0],
          StartingPoints[it+1][1]-StartingPoints[it-1][1])
    v2 = (ENS[it]-ENS[it-1],
          StartingPoints[it][0]-StartingPoints[it-1][0],
          StartingPoints[it][1]-StartingPoints[it-1][1])
    vnormal = (v1[1]*v2[2]-v1[2]*v2[1],
               v1[2]*v2[0]-v1[0]*v2[2],
               v1[0]*v2[1]-v1[1]*v2[0])
    j = 1
    while abs(vnormal[0]) < eps:
        v1 = (ENS[it+1]-ENS[it-1-j],
              StartingPoints[it+1][0]-StartingPoints[it-1-j][0],
              StartingPoints[it+1][1]-StartingPoints[it-1-j][1])
        v2 = (ENS[it-j]-ENS[it-1-j],
              StartingPoints[it-j][0]-StartingPoints[it-1-j][0],
              StartingPoints[it-j][1]-StartingPoints[it-1-j][1])
        vnormal = (v1[1]*v2[2]-v1[2]*v2[1],
                   v1[2]*v2[0]-v1[0]*v2[2],
                   v1[0]*v2[1]-v1[1]*v2[0])
        j += 1
    vnormal = (1, vnormal[1]/vnormal[0], vnormal[2]/vnormal[0])
    K = vnormal[0]*ENS[it+1] + vnormal[1]*StartingPoints[it+1][0] + vnormal[2]*StartingPoints[it+1][1]
    plano = (vnormal[0] * master_instance1.SLAVE_SECURITY +
             vnormal[1] * master_instance1.REQ_RES_Z1 +
             vnormal[2] * master_instance1.REQ_RES_Z2 -
             K)
    print plano
    planos[it-1] = plano

    if vnormal[0] > 0:
        master_instance1.CT_cortes.add(plano >= 0)
        master_instance1.preprocess()
    elif vnormal[0] < 0:
        master_instance1.CT_cortes.add(plano <= 0)
        master_instance1.preprocess()

    if ENS[it+1] <= GAP_ENS:
        is_opt = True

    if it > max_it:
        is_opt = True

fopt = 100000000
ropt = 0
# m2 = m1
print 'Particion 1:\n (Req1, Req2) ENS Fobj'
for r in StartingPoints:
    print r, StartingPoints[r], ENS[r], '[MW]', fobj[r]/1000, '[k$]'
    if ENS[r] == 0:
        if fobj[r] < fopt:
            fopt = fobj[r]
            ropt = r
'Cortes:'
for r in planos:
    print planos[r], '>= 0'
# print 'Particion 2:\n (Req1, Req2) Fobj'
# for r in values2:
#     print r, values2[r]
#     if values2[r] < m2:
#         m2 = values2[r]
#         rr2 = r


print '\nOptimo Particion 1=', StartingPoints[ropt], fopt
# print 'Optimo Particion 2=', rr, m2
# TODO Agregar corte de benders



print ('\n--------M O D E L O : T E R M I N A D O --------' )
print ("path input:" + path_datos + '\n')
# master_instance.CT_benders_reserve_requirement.pprint()

# ------R E S U L T A D O S------------------------------------------------------------------------------
print ('------E S C R I B I E N D O --- R E S U L T A D O S------\n')
#
# # Resultados para GENERADORES ---------------------------------------------------
# exporter.exportar_gen(master_instance, path_resultados)
# # Resultados para LINEAS --------------------------------------------------------
# exporter.exportar_lin(master_instance, path_resultados)
# # Resultados para BARRAS (ENS)---------------------------------------------------
# exporter.exportar_bar(master_instance, path_resultados)
# # Resultados del sistema --------------------------------------------------------
# exporter.exportar_system(master_instance, path_resultados)
# # Resultados de zonas -----------------------------------------------------------
# exporter.exportar_zones(master_instance, path_resultados)
#


