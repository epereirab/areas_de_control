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

path_datos = 'Data/Un Escenario/'

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
data_master2 = data_master

data_master.load(filename=path_datos+'data_config_SIC-SING.csv',
                 param=master_model.config_value,
                 index=master_model.CONFIG)

data_slave = data_master


print ("--- Creando Master ---")
master_instance1 = master_model.create(data_master)

data_master2.load(filename=path_datos+'data_config_CN-CENTRO.csv',
                  param=master_model.config_value,
                  index=master_model.CONFIG)
master_instance2 = master_model.create(data_master2)

print ("--- Creando Slave")
slave_instance = slave_model.create(data_slave)

opt = SolverFactory("cplex")

# Datos para la iteracion

GAP_ENS = 1
minR = 100
i = 1
values1 = {}
for req1 in range(100, 200, 50):
    for req2 in range(100, 200, 50):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
        if req1+req2 >= minR:

            print ('\n\nIteracion %i' % i)
            i = i+1
            print ("--- Resolviendo la optimizacion del MASTER---")
            master_instance1.Req_Z1 = req1
            master_instance1.Req_Z2 = req2
            master_instance1.preprocess()
            results_master = opt.solve(master_instance1, tee=False)
            print ("Master Resuelto")
            # results_master.write()
            master_instance1.load(results_master)

            # Update of slave dispatch parameters
            for g in master_instance1.GENERADORES:
                for s in master_instance1.ESCENARIOS:
                    # if master_instance.GEN_UC[g, s].value is None:
                    #    slave_instance.gen_d_uc[g, s] = 0
                    # else:
                    #    slave_instance.gen_d_uc[g, s] = master_instance.GEN_UC[g, s].value
                    slave_instance.gen_d_pg[g, s] = min(master_instance1.GEN_PG[g, s].value,
                                                        slave_instance.gen_pmax[g] * slave_instance.gen_factorcap[g, s])
                    slave_instance.gen_d_resup[g, s] = master_instance1.GEN_RESUP[g, s].value
                # print slave_instance.gen_pmax[g]

            print 'Updating Slave'

            slave_instance.preprocess()

            print ("--- Resolviendo la optimizacion del SLAVE---")
            results_slave = opt.solve(slave_instance, tee=False)  # tee=True shows the solver info
            # results.write()
            slave_instance.load(results_slave)

            if slave_instance.Objective_rule()/slave_instance.config_value['voll'] <= GAP_ENS:
                print ('Requerimiento de reserva zona 1: %r' % master_instance1.Req_Z1.value)
                print ('Requerimiento de reserva zona 2: %r' % master_instance1.Req_Z2.value)
                print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))
                print ('Costo Operacional del Sistema: %r [k$]' % (master_instance1.Objective_rule()/1000))
                values1[req1, req2] = (master_instance1.Objective_rule()/1000)
                break
            print ('Requerimiento de reserva zona 1: %r' % master_instance1.Req_Z1.value)
            print ('Requerimiento de reserva zona 2: %r' % master_instance1.Req_Z2.value)
            print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))

i = 1
values2 = {}
print '\n Comienzo de sampleo particion 2'
for req1 in range(100, 200, 50):
    for req2 in range(100, 200, 50):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
        if req1+req2 >= minR:

            print ('\n\nIteracion %i' % i)
            i = i+1
            print ("--- Resolviendo la optimizacion del MASTER---")
            master_instance2.Req_Z1 = req1
            master_instance2.Req_Z2 = req2
            master_instance2.preprocess()
            results_master = opt.solve(master_instance2, tee=False)
            print ("Master Resuelto")
            # results_master.write()
            master_instance2.load(results_master)

            # Update of slave dispatch parameters
            for g in master_instance2.GENERADORES:
                for s in master_instance2.ESCENARIOS:
                    # if master_instance.GEN_UC[g, s].value is None:
                    #    slave_instance.gen_d_uc[g, s] = 0
                    # else:
                    #    slave_instance.gen_d_uc[g, s] = master_instance.GEN_UC[g, s].value
                    slave_instance.gen_d_pg[g, s] = min(master_instance2.GEN_PG[g, s].value,
                                                        slave_instance.gen_pmax[g] * slave_instance.gen_factorcap[g, s])
                    slave_instance.gen_d_resup[g, s] = master_instance2.GEN_RESUP[g, s].value
                # print slave_instance.gen_pmax[g]

            print 'Updating Slave'

            slave_instance.preprocess()

            print ("--- Resolviendo la optimizacion del SLAVE---")
            results_slave = opt.solve(slave_instance, tee=False)  # tee=True shows the solver info
            # results.write()
            slave_instance.load(results_slave)

            if slave_instance.Objective_rule()/slave_instance.config_value['voll'] <= GAP_ENS:
                print ('Requerimiento de reserva zona 1: %r' % master_instance2.Req_Z1.value)
                print ('Requerimiento de reserva zona 2: %r' % master_instance2.Req_Z2.value)
                print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))
                print ('Costo Operacional del Sistema: %r [k$]' % (master_instance2.Objective_rule()/1000))
                values2[req1, req2] = (master_instance2.Objective_rule()/1000)
                break
            print ('Requerimiento de reserva zona 1: %r' % master_instance2.Req_Z1.value)
            print ('Requerimiento de reserva zona 2: %r' % master_instance2.Req_Z2.value)
            print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))

m1 = 100000000
m2 = m1
rr = []
rr2 = []
print 'Particion 1:\n (Req1, Req2) Fobj'
for r in values1:
    print r, values1[r]
    if values1[r] < m1:
        m1 = values1[r]
        rr = r
print 'Particion 2:\n (Req1, Req2) Fobj'
for r in values2:
    print r, values2[r]
    if values2[r] < m2:
        m2 = values2[r]
        rr2 = r


print '\nOptimo Particion 1=', rr, m1
print 'Optimo Particion 2=', rr2, m2
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
#
#
#
#
#
#
