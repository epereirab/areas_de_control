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

data_master.load(filename=path_datos+'data_config_CENTRO-SUR.csv',
                 param=master_model.config_value,
                 index=master_model.CONFIG)

data_master.load(filename=path_datos+'data_scenarios.csv',
                 set=master_model.ESCENARIOS)
#data_master.load(filename=path_datos+'data_particiones.csv',
#                 param=(master_model.barras_zona1, master_model.barras_zona2),
#                 index=master_model.PARTICIONES)

data_slave = data_master

#data_slave.load(filename=path_datos+'data_gen_despachos.csv',
#                param=(slave_model.gen_d_uc, slave_model.gen_d_pg, slave_model.gen_d_resup),
#                index=(slave_model.GENERADORES, slave_model.ESCENARIOS))

print ("--- Creando Master ---")
master_instance = master_model.create(data_master)
master_instance.CT_fix_req_res_z1.deactivate()
master_instance.CT_fix_req_res_z2.deactivate()
print ("--- Creando Slave---")
slave_instance = slave_model.create(data_slave)

opt = SolverFactory("cplex")

# Datos para la iteracion

max_it = 20
GAP_ENS = 20

ngen = {}

ngen[1] = sum(1 for g in master_instance.GENERADORES
              if master_instance.zona[master_instance.gen_barra[g]] == 1
              if master_instance.gen_tipo[g] in ['GNL', 'Embalse', 'Carbon', 'Diesel'])
ngen[2] = sum(1 for g in master_instance.GENERADORES
              if master_instance.zona[master_instance.gen_barra[g]] == 2
              if master_instance.gen_tipo[g] in ['GNL', 'Embalse', 'Carbon', 'Diesel'])
ENS = {}
fobj = {}
reqs = {}

print ngen
planos = {}
for i in range(1, max_it+1):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
    print ('\n\nIteracion %i' % i)
    print ("--- Resolviendo la optimizacion del MASTER---")
    results_master = opt.solve(master_instance, tee=False)
    print ("Master Resuelto")
    # results_master.write()
    master_instance.load(results_master)
    reqs[i] = (master_instance.REQ_RES_Z1.value, master_instance.REQ_RES_Z2.value)
    print ('Requerimiento de reserva zona 1: %r' % reqs[i][0])
    print ('Requerimiento de reserva zona 2: %r' % reqs[i][1])


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

    print 'Updating Slave'

    # slave_instance.preprocess()

    # print('Pmin | P_f   | Res   | R+P |   Pmax')
    # for g in slave_instance.GENERADORES:
    #     print('%r ,   %r,  %r, %r,  %r' % (
    #         slave_instance.gen_pmin[g],
    #         slave_instance.gen_d_pg[g,'Seco.Dmin'].value,
    #         slave_instance.gen_d_resup[g,'Seco.Dmin'].value,
    #         slave_instance.gen_d_pg[g,'Seco.Dmin'].value + slave_instance.gen_d_resup[g,'Seco.Dmin'].value,
    #         slave_instance.gen_pmax[g] * slave_instance.gen_factorcap[g, s]))


    print ("--- Resolviendo la optimizacion del SLAVE---")
    results_slave = opt.solve(slave_instance, tee=False)  # tee=True shows the solver info
    # results.write()
    slave_instance.load(results_slave)

    ENS[i] = slave_instance.Objective_rule()
    fobj[i] = master_instance.Objective_rule()/1000
    print ('ENS de la particion: %r [MW]' % ENS[i])
    print ('ENS esperada (Master): %r [MW]' % master_instance.SLAVE_SECURITY.value)
    print ('Costo Operacional del Sistema: %r [k$]' % fobj[i])
    if ENS[i] <= GAP_ENS:
        break

    duales = slave_instance.dual
    cut = (slave_instance.Objective_rule() +
           sum(duales.getValue(slave_instance.CT_forced_resup[g, s])
               for g in slave_instance.GENERADORES
               for s in slave_instance.ESCENARIOS
               if master_instance.zona[master_instance.gen_barra[g]] == 1) / ngen[1] *
           (master_instance.REQ_RES_Z1-master_instance.REQ_RES_Z1.value) +
           sum(duales.getValue(slave_instance.CT_forced_resup[g, s])
               for g in slave_instance.GENERADORES
               for s in slave_instance.ESCENARIOS
               if master_instance.zona[master_instance.gen_barra[g]] == 2) / ngen[2] *
           (master_instance.REQ_RES_Z2-master_instance.REQ_RES_Z2.value)
           )
    master_instance.CT_cortes.add(master_instance.SLAVE_SECURITY >= cut)
    master_instance.preprocess()
    planos[i] = (master_instance.SLAVE_SECURITY >= cut)
    print 'corte:', planos[i]

    # for s in slave_instance.ESCENARIOS:
    #     for g in slave_instance.GENERADORES:
    #         if slave_instance.gen_tipo[g] in ['Serie', 'Pasada', 'Solar', 'Eolico']:
    #             print ('Pg ' + g + ', ' + s + ': ' + str(duales.getValue(slave_instance.CT_forced_resup[g,s])) + ' MW')



# TODO Agregar corte de benders
print '\nCORTES'
for i in range(1, len(planos)+1):
    print str(i) + ': ' + str(planos[i])
print '\n Funcion Objetivo [k$]'
for i in fobj:
    print str(i) + ': ' + str(fobj[i])
print '\n ENS [MW]'
for i in ENS:
    print str(i) + ': ' + str(ENS[i])
print '\n Requerimientos (Zona1, Zona2) [MW]'
for i in range(1, len(reqs)+1):
    print str(i) + ': ' + str(reqs[i][0]) + ' ' + str(reqs[i][1])

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
