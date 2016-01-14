from coopr.pyomo import *
from coopr.opt import SolverFactory

from Master_DEconRRyPart import _model as master_model
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

max_it = 20
GAP_ENS = 1

ngen = {}
for p in master_instance.PARTICIONES:
    ngen[p, 1] = sum(1 for g in master_instance.GENERADORES
                     if master_instance.zona[master_instance.gen_barra[g], p] == 1)
    ngen[p, 2] = sum(1 for g in master_instance.GENERADORES
                     if master_instance.zona[master_instance.gen_barra[g], p] == 2)

print ngen
planos = {}
for i in range(1, max_it+1):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
    print ('\n\nIteracion %i' % i)
    print ("--- Resolviendo la optimizacion del MASTER---")
    results_master = opt.solve(master_instance, tee=True)
    print ("Master Resuelto")
    # results_master.write()
    master_instance.load(results_master)
    for p in master_instance.PARTICIONES:

        if round(master_instance.C_PART[p].value, 0):
            parti = p
            print ('Particion ' + parti + ' seleccionada')
            print ('Requerimiento de reserva zona 1: %r' % master_instance.REQ_RES_Z1[parti].value)
            print ('Requerimiento de reserva zona 2: %r' % master_instance.REQ_RES_Z2[parti].value)
            break

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

    slave_instance.preprocess()

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

    if slave_instance.Objective_rule()/slave_instance.config_value['voll'] <= GAP_ENS:
        print('Particion optima encontrada: %s' % parti)
        print ('Requerimiento de reserva zona 1: %r' % master_instance.REQ_RES_Z1[parti].value)
        print ('Requerimiento de reserva zona 2: %r' % master_instance.REQ_RES_Z2[parti].value)
        print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))
        print ('Costo Operacional del Sistema: %r [k$]' % (master_instance.Objective_rule()/1000))
        break
    print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))

    # for s in slave_instance.ESCENARIOS:
    #     for g in slave_instance.GENERADORES:
    #         print ('Pg ' + g + ', ' + s + ': ' + str(slave_instance.GEN_PG[g, s].value) + ' MW')
    # slave_instance.CT_forced_pg.pprint()

    duales = slave_instance.dual
    cut = (slave_instance.Objective_rule() +
           sum(duales.getValue(slave_instance.CT_forced_resup[g, s])
               for g in slave_instance.GENERADORES
               for s in slave_instance.ESCENARIOS
               if master_instance.zona[master_instance.gen_barra[g], parti] == 1) / ngen[parti, 1] *
           (master_instance.REQ_RES_Z1[parti]-master_instance.REQ_RES_Z1[parti].value) +
           sum(duales.getValue(slave_instance.CT_forced_resup[g, s])
               for g in slave_instance.GENERADORES
               for s in slave_instance.ESCENARIOS
               if master_instance.zona[master_instance.gen_barra[g], parti] == 2) / ngen[parti, 2] *
           (master_instance.REQ_RES_Z2[parti]-master_instance.REQ_RES_Z2[parti].value)
           )
    master_instance.BENDERS.add(i)
    master_instance.CT_benders_reserve_requirement.add(master_instance.SLAVE_SECURITY >= cut)
    master_instance.preprocess()
    planos[i, parti] = (master_instance.SLAVE_SECURITY >= cut)
    print planos[i, parti]
# TODO Agregar corte de benders
for i in planos:
    print planos[i]


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
