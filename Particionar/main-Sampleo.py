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

data_master.load(filename=path_datos+'data_config_CENTRO-SUR.csv',
                 param=master_model.config_value,
                 index=master_model.CONFIG)

data_slave = data_master


print ("--- Creando Master ---")
master_instance1 = master_model.create(data_master)

print ("--- Creando Slave")
slave_instance = slave_model.create(data_slave)

opt = SolverFactory("cplex")

# Datos para la iteracion

GAP_ENS = 1
minR = 100
i = 1
ENS = {}
fobj = {}
reqs = {}

for req1 in range(600, 850, 50):
    for req2 in range(450, 451, 50):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
        if req1+req2 >= minR:
            reqs[i] = (req1, req2)
            print ('\n\nIteracion %i' % i)
            print ('Req 1: %i, Req 2: %i' % (req1, req2))

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

            #slave_instance.preprocess()

            print ("--- Resolviendo la optimizacion del SLAVE---")
            results_slave = opt.solve(slave_instance, tee=False)  # tee=True shows the solver info
            # results.write()
            slave_instance.load(results_slave)

            ENS[i] = slave_instance.Objective_rule()
            fobj[i] = master_instance1.Objective_rule()/1000
            print ('Requerimiento de reserva zona 1: %r' % req1)
            print ('Requerimiento de reserva zona 2: %r' % req2)
            print ('ENS de la particion: %r [MW]' % ENS[i])
            print ('Costo Operacional del Sistema: %r [k$]' % fobj[i])
            i += 1
            if ENS[i-1] <= GAP_ENS:
                break


fopt = 100000000
rr = []
print 'Particion 1:\nit (Req1, Req2) ENS   Fobj'
for i in reqs:
    print i, ' ', reqs[i], ' ', ENS[i], fobj[i]
    if ENS[i] == 0:
        if fobj[i] < fopt:
            rr = reqs[i]
            fopt = fobj[i]



print '\nOptimo Particion 1=', rr, fopt

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
