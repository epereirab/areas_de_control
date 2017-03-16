from coopr.pyomo import *
from coopr.opt import SolverFactory

from Master_DEconRRyPart import _model as master_model
from SlaveModel import _model as slave_model
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

if not os.path.exists(path_resultados):
    print "el directorio output: " + path_resultados + " no existe, creando..."
    os.mkdir(path_resultados)

# - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -
#  - - - - - - CARGAR DATOS AL MODELO  - - - - - - ##
#  - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -

print ("--- Leyendo data ---")
print ("path input:" + path_datos)
data_master = DataPortal()

nombre_archivo=path_datos+'data_gen_static.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=(master_model.gen_barra, master_model.gen_pmax, master_model.gen_pmin, master_model.gen_falla,
                        master_model.gen_cfijo, master_model.gen_tipo, master_model.gen_cvar0, master_model.gen_rupmax0,
                        master_model.gen_rdnmax0),
                 index=master_model.GENERADORES)
print 'importacion OK'

nombre_archivo=path_datos+'data_gen_dyn.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=(master_model.gen_cvar, master_model.gen_rupmax, master_model.gen_rdnmax,
                        master_model.gen_factorcap),
                 index=(master_model.GENERADORES, master_model.ESCENARIOS))
print 'importacion OK'

nombre_archivo=path_datos+'data_lin.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=(master_model.linea_fmax, master_model.linea_barA, master_model.linea_barB,
                        master_model.linea_available, master_model.linea_x, master_model.linea_falla),
                 index=master_model.LINEAS)
print 'importacion OK'

nombre_archivo=path_datos+'data_bar_static.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=master_model.vecinos,
                 index=master_model.BARRAS)
print 'importacion OK'

nombre_archivo=path_datos+'data_bar_dyn.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=master_model.demanda,
                 index=(master_model.BARRAS, master_model.ESCENARIOS))
print 'importacion OK'

nombre_archivo=path_datos+'data_config.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=master_model.config_value,
                 index=master_model.CONFIG)
print 'importacion OK'

nombre_archivo=path_datos+'data_scenarios.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 set=master_model.ESCENARIOS)
print 'importacion OK'

nombre_archivo=path_datos+'data_particiones.csv'
print "importando: " + nombre_archivo
data_master.load(filename=nombre_archivo,
                 param=(master_model.barras_zona1, master_model.barras_zona2),
                 index=master_model.PARTICIONES)

#data_master.load(filename=path_datos+'data_contingencias_dyn.csv',
#          param=(master_model.factor_contingencia, master_model.centrales_contingencia,master_model.lineas_contingencia),
#          index=master_model.CONTINGENCIAS)

data_slave = data_master

#data_slave.load(filename=path_datos+'data_gen_despachos.csv',
#                param=(slave_model.gen_d_uc, slave_model.gen_d_pg, slave_model.gen_d_resup),
#                index=(slave_model.GENERADORES, slave_model.ESCENARIOS))

# - - - - - - - - - - - - - - - - - - - - - - - -  - - - - - - - - - - - -

print ("--- Creando Master ---")
master_instance = master_model.create(data_master)

#exporter.exportar_modelo(master_instance, path_resultados,'master_model')

print ("--- Creando Slave")
slave_instance = slave_model.create(data_slave)

#exporter.exportar_modelo(slave_instance, path_resultados,'slave_model')

opt = SolverFactory("cplex")

# Datos para la iteracion

max_it = 50
GAP_ENS = 1

ngen = {}
for p in master_instance.PARTICIONES:
    ngen[p, 1] = sum(1 for g in master_instance.GENERADORES
                     if master_instance.zona[master_instance.gen_barra[g], p] == 1
                     if master_instance.gen_tipo[g] in ['GNL', 'Embalse', 'Carbon', 'Diesel'])
    ngen[p, 2] = sum(1 for g in master_instance.GENERADORES
                     if master_instance.zona[master_instance.gen_barra[g], p] == 2
                     if master_instance.gen_tipo[g] in ['GNL', 'Embalse', 'Carbon', 'Diesel'])

print ngen
planos = {}
ENS = {}
fobj = {}
reqs = {}
particiones = {}

for i in range(1, max_it+1):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
    print ('\n\nIteracion %i' % i)
    print ("--- Resolviendo la optimizacion del MASTER---")
    results_master = opt.solve(master_instance, tee=False)
    print ("Master Resuelto")
    # results_master.write()
    master_instance.load(results_master)

    for p in master_instance.PARTICIONES:
        if round(master_instance.C_PART[p].value, 0):
            parti = p
            print ('PARTICION ' + parti + ' SELECCIONADA')
            particiones[i] = p
            for s in master_instance.ESCENARIOS:
                print 'resultados escenario: ' +str(s)
                reqs[i, p, s] = (master_instance.REQ_RES_Z1[p, s].value, master_instance.REQ_RES_Z2[p,s].value)

                print ('Requerimiento de reserva zona 1: %r' % reqs[i, p, s][0])
                print ('Requerimiento de reserva zona 2: %r' % reqs[i, p, s][1])
            break

    # Update of slave dispatch parameters
    for g in master_instance.GENERADORES:
        for s in master_instance.ESCENARIOS:
            # if master_instance.GEN_UC[g, s].value is None:
            #    slave_instance.gen_d_uc[g, s] = 0
            # else:
            #    slave_instance.gen_d_uc[g, s] = master_instance.GEN_UC[g, s].value
            slave_instance.gen_d_pg[g, s] = round(min(master_instance.GEN_PG[g, s].value,
                                                slave_instance.gen_pmax[g] * slave_instance.gen_factorcap[g, s]),2)
            slave_instance.gen_d_resup[g, s] = round(master_instance.GEN_RESUP[g, s].value,2)
            #print 'solucion master: PG(g,s)= P ' + str(g) + ' '+ str(s) + ' '+str(slave_instance.gen_d_pg[g, s].value) +'Res=' + str(g) + ' '+ str(s) + ' '+str(slave_instance.gen_d_resup[g, s].value)
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

    imprimir_master = False
    imprimir_slave = True


    if imprimir_master:
        exporter.exportar_modelo(master_instance, path_resultados,'master_model_resuelto')

    if imprimir_slave:
        exporter.exportar_modelo(slave_instance, path_resultados,'slave_model_resuelto')



    ENS[i] = slave_instance.Objective_rule()
    fobj[i] = master_instance.Objective_rule()/1000
    print ('ENS de la particion: %r [MW]' % ENS[i])
    print ('ENS esperada (Master): %r [MW]' % master_instance.SLAVE_SECURITY.value)
    print ('Costo Operacional del Sistema: %r [k$]' % fobj[i])
    if ENS[i] <= GAP_ENS:
        break

    # for s in slave_instance.ESCENARIOS:
    #     for g in slave_instance.GENERADORES:
    #         print ('Pg ' + g + ', ' + s + ': ' + str(slave_instance.GEN_PG[g, s].value) + ' MW')
    # slave_instance.CT_forced_pg.pprint()

    duales = slave_instance.dual
    cut = (slave_instance.Objective_rule() +
           sum(duales.getValue(slave_instance.CT_forced_resup[g, s])*
           (master_instance.REQ_RES_Z1[parti, s]-master_instance.REQ_RES_Z1[parti, s].value)
               for g in slave_instance.GENERADORES
               for s in slave_instance.ESCENARIOS
               if master_instance.zona[master_instance.gen_barra[g], parti] == 1) / ngen[parti, 1]  +

           sum(duales.getValue(slave_instance.CT_forced_resup[g, s]) *
           (master_instance.REQ_RES_Z2[parti,s]-master_instance.REQ_RES_Z2[parti,s].value)
               for g in slave_instance.GENERADORES
               for s in slave_instance.ESCENARIOS
               if master_instance.zona[master_instance.gen_barra[g], parti] == 2) / ngen[parti, 2]
           )
    master_instance.CT_cortes.add(master_instance.SLAVE_SECURITY >= cut)
    master_instance.preprocess()
    planos[i, parti] = (master_instance.SLAVE_SECURITY >= cut)
    print planos[i, parti]

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
#exporter.exportar_gen_master_model(master_instance, path_resultados)
#exporter.exportar_gen_slave_model(slave_instance, path_resultados)
# # Resultados para LINEAS --------------------------------------------------------
#exporter.exportar_lin_master_model(master_instance, path_resultados)
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
