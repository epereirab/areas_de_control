from coopr.pyomo import *
from coopr.opt import SolverFactory

from Master_DEconRRyPart import _model as master_model
from Master_DEconRR import _model as master1p
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
print ("path input:" + path_datos)

data_master = DataPortal()

path_datos = 'Data/completo/'

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

data_master.load(filename=path_datos+'data_config.csv',
                 param=master_model.config_value,
                 index=master_model.CONFIG)

data_master.load(filename=path_datos+'data_scenarios.csv',
                 set=master_model.ESCENARIOS)
data_master1p = data_master
data_master.load(filename=path_datos+'data_particiones.csv',
                 param=(master_model.barras_zona1, master_model.barras_zona2),
                 index=master_model.PARTICIONES)

data_slave = data_master

#data_slave.load(filename=path_datos+'data_gen_despachos.csv',
#                param=(slave_model.gen_d_uc, slave_model.gen_d_pg, slave_model.gen_d_resup),
#                index=(slave_model.GENERADORES, slave_model.ESCENARIOS))

print ("--- Creando Master ---")
master_instance = master_model.create(data_master)
print ("--- Creando Slave")
slave_instance = slave_model.create(data_slave)

opt = SolverFactory("cplex")

# Datos para la iteracion

max_it = 30
GAP_ENS = 1

ngen = {}
planos = {}
ENS = {}
fobj = {}
reqs = {}
particiones = {}
it = 1
eps = 0.1

def solve_despacho_y_confiabilidad(master, slave, req1, req2):
    master.Req_Z1 = req1
    master.Req_Z2 = req2
    # master.preprocess()
    results_m = opt.solve(master, tee=False)
    print ("Master Resuelto")
    # results_master.write()
    master.load(results_m)

    # Update of slave dispatch parameters
    for g in master.GENERADORES:
        for s in master.ESCENARIOS:
            slave.gen_d_pg[g, s] = min(master.GEN_PG[g, s].value,
                                       slave.gen_pmax[g] * slave.gen_factorcap[g, s])
            slave.gen_d_resup[g, s] = master.GEN_RESUP[g, s].value

    print 'Updating Slave'
    print ("--- Resolviendo la optimizacion del SLAVE---")
    results_sl = opt.solve(slave, tee=False)  # tee=True shows the solver info
    slave.load(results_sl)

    return master.Objective_rule(), slave.Objective_rule()

# Resolviendo puntos de partida
print '\nSolving Starting Points'
Requerimientos = {}
contador = {}
for p in master_instance.PARTICIONES:
    Requerimientos[0, p] = (100, 100)
    Requerimientos[1, p] = (150, 100)
    Requerimientos[2, p] = (100, 150)
    for i in [0, 1, 2]:
        print ("--- Creando Master -- ", p)
        data_master1p.load(filename=path_datos+'data_config_'+p+'.csv',
                           param=master_model.config_value,
                           index=master_model.CONFIG)
        master1p = master1p.create(data_master1p)
        print '\nStarting point', i+1, ' ', p
        [fobj[i, p], ENS[i, p]] = solve_despacho_y_confiabilidad(master1p, slave_instance,
                                                                 Requerimientos[i, p][0], Requerimientos[i, p][1])
        print 'ENS de la particion ', p, ' del punto ', Requerimientos[i, p], ' = ', ENS[i, p], ' [MW]'

    v1 = [ENS[2, p]-ENS[0, p],
          Requerimientos[2, p][0]-Requerimientos[0, p][0],
          Requerimientos[2, p][1]-Requerimientos[0, p][1]]
    v2 = [ENS[it, p]-ENS[1, p],
          Requerimientos[1, p][0]-Requerimientos[0, p][0],
          Requerimientos[1, p][1]-Requerimientos[0, p][1]]
    vnormal = [v1[1]*v2[2]-v1[2]*v2[1],
               v1[2]*v2[0]-v1[0]*v2[2],
               v1[0]*v2[1]-v1[1]*v2[0]]
    vnormal = [1, vnormal[1]/vnormal[0], vnormal[2]/vnormal[0]]
    K = vnormal[0]*ENS[0, p] + vnormal[1]*Requerimientos[0, p][0] + vnormal[2]*Requerimientos[0, p][1]

    plano = (vnormal[0] * master_instance.SLAVE_SECURITY +
             vnormal[1] * master_instance.REQ_RES_Z1[p] +
             vnormal[2] * master_instance.REQ_RES_Z2[p] -
             K)
    master_instance.CT_cortes.add(plano >= 0)

    print 'Corte particion ', p, ': ', plano
    planos[0, p] = plano
    contador[p] = 2

master_instance.preprocess()
is_opt = False

while not is_opt:
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
    it += 1
    print ('\n\nIteracion %i' % it)
    print ("--- Resolviendo la optimizacion del MASTER---")
    results_master = opt.solve(master_instance, tee=False)
    print ("Master Resuelto")
    # results_master.write()
    master_instance.load(results_master)

    for p in master_instance.PARTICIONES:

        if round(master_instance.C_PART[p].value, 0):
            parti = p
            particiones[it] = p
            contador[p] += 1
            Requerimientos[contador[p], p] = [master_instance.REQ_RES_Z1[p].value, master_instance.REQ_RES_Z2[p].value]

            print ('Particion ' + parti + ' seleccionada')
            print ('Requerimiento de reserva zona 1: %r' % Requerimientos[contador[p], p][0])
            print ('Requerimiento de reserva zona 2: %r' % Requerimientos[contador[p], p][1])
            break

    print 'Updating Slave'
    # Update of slave dispatch parameters
    for g in master_instance.GENERADORES:
        for s in master_instance.ESCENARIOS:
            # if master_instance.GEN_UC[g, s].value is None:
            #    slave_instance.gen_d_uc[g, s] = 0
            # else:
            #    slave_instance.gen_d_uc[g, s] = master_instance.GEN_UC[g, s].value
            slave_instance.gen_d_pg[g, s] = min(master_instance.GEN_PG[g, s].value,
                                                slave_instance.gen_pmax[g] * slave_instance.gen_factorcap[g, s])
            slave_instance.gen_d_resup[g, s] = master_instance.GEN_RESUP[g, s].value
        # print slave_instance.gen_pmax[g]

    print ("--- Resolviendo la optimizacion del SLAVE---")
    results_slave = opt.solve(slave_instance, tee=False)  # tee=True shows the solver info
    # results.write()
    slave_instance.load(results_slave)

    ENS[contador[p], p] = slave_instance.Objective_rule()
    fobj[contador[p], p] = master_instance.Objective_rule()/1000
    print ('ENS de la particion: %r [MW]' % ENS[contador[p], p])
    print ('ENS esperada (Master): %r [MW]' % master_instance.SLAVE_SECURITY.value)
    print ('Costo Operacional del Sistema: %r [k$]' % fobj[contador[p], p])

    # for s in slave_instance.ESCENARIOS:
    #     for g in slave_instance.GENERADORES:
    #         print ('Pg ' + g + ', ' + s + ': ' + str(slave_instance.GEN_PG[g, s].value) + ' MW')
    # slave_instance.CT_forced_pg.pprint()

    v1 = [ENS[contador[p], p]-ENS[contador[p]-1, p],
          Requerimientos[contador[p], p][0]-Requerimientos[contador[p]-1, p][0],
          Requerimientos[contador[p], p][1]-Requerimientos[contador[p]-1, p][1]]
    v2 = [ENS[contador[p], p]-ENS[contador[p]-2, p],
          Requerimientos[contador[p], p][0]-Requerimientos[contador[p]-2, p][0],
          Requerimientos[contador[p], p][1]-Requerimientos[contador[p]-2, p][1]]
    vnormal = [v1[1]*v2[2]-v1[2]*v2[1],
               v1[2]*v2[0]-v1[0]*v2[2],
               v1[0]*v2[1]-v1[1]*v2[0]]
    j = 1
    planovalido = False
    while not planovalido:
        while abs(vnormal[0]) < eps:
            v1 = [ENS[contador[p], p]-ENS[contador[p]-j, p],
                  Requerimientos[contador[p], p][0]-Requerimientos[contador[p]-j, p][0],
                  Requerimientos[contador[p], p][1]-Requerimientos[contador[p]-j, p][1]]
            v2 = [ENS[contador[p], p]-ENS[contador[p]-j-1, p],
                  Requerimientos[contador[p], p][0]-Requerimientos[contador[p]-j-1, p][0],
                  Requerimientos[contador[p], p][1]-Requerimientos[contador[p]-j-1, p][1]]
            vnormal = [v1[1]*v2[2]-v1[2]*v2[1],
                       v1[2]*v2[0]-v1[0]*v2[2],
                       v1[0]*v2[1]-v1[1]*v2[0]]
            j += 1
        vnormal = [1, vnormal[1]/vnormal[0], vnormal[2]/vnormal[0]]
        K = vnormal[0]*ENS[contador[p], p] + \
            vnormal[1]*Requerimientos[contador[p], p][0] + \
            vnormal[2]*Requerimientos[contador[p], p][1]

        if K > 0 and vnormal[1] >= 0 and vnormal[2] >= 0:
            planovalido = True
        else:
            vnormal[0] = 0

    plano = (vnormal[0] * master_instance.SLAVE_SECURITY +
             vnormal[1] * master_instance.REQ_RES_Z1[p] +
             vnormal[2] * master_instance.REQ_RES_Z2[p] -
             K)
    planos[it-1] = plano

    master_instance.CT_cortes.add(plano >= 0)
    master_instance.preprocess()

    if ENS[contador[p], p] <= GAP_ENS:
        is_opt = True

    if it > max_it:
        is_opt = True

    master_instance.preprocess()
    planos[it, parti] = plano
    print planos[it, parti]

# TODO Agregar corte de benders
print '\nCORTES'
for i in planos:
    print str(i) + ': ' + str(planos[i])
print '\n Funcion Objetivo [k$]'
for i in fobj:
    print str(i) + ': ' + str(fobj[i])
print '\n ENS [MW]'
for i in ENS:
    print str(i) + ': ' + str(ENS[i])
print '\n Requerimientos (Zona1, Zona2) [MW]'
for i in reqs:
    print str(i) + ': ' + str(reqs[i])
print '\n Particion seleccionada en iteracion i'
for i in particiones:
    print str(i) + ': ' + str(particiones[i])


print ('\n--------M O D E L O :  "%s"  T E R M I N A D O --------' % master_instance.config_value['scuc'])
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
#
#
#
#
#
#

