from coopr.pyomo import *
from coopr.opt import SolverFactory

from MasterModel import _model as master_model
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

#  - - - - - - CARGAR DATOS AL MODELO  - - - - - - ##

print ("--- Leyendo data ---")
print ("path input:" + path_datos)

data_master = DataPortal()


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

data_slave.load(filename=path_datos+'data_gen_despachos.csv',
                param=(slave_model.gen_d_uc, slave_model.gen_d_pg, slave_model.gen_d_resup),
                index=(slave_model.GENERADORES, slave_model.ESCENARIOS))

print ("--- Creando Modelo ---")
master_instance = master_model.create(data_master)
slave_instance = slave_model.create(data_slave)

opt = SolverFactory("cplex")

# Datos para la iteracion

max_it = 2
GAP_ENS = 1

for i in range(1, max_it):
####  - - - -   - - RESOLVIENDO LA OPTIMIZACION  MAESTRO- - - - - - #######
    print ('Iteracion %i' % i)
    print ("--- Resolviendo la optimizacion del MASTER---")
    results_master = opt.solve(master_instance, tee=True)
    # results_master.write()
    master_instance.load(results_master)
    for p in master_instance.PARTICIONES:
        if master_instance.C_PART[p].value:
            parti = p
            print ('Particion ' + p + ' seleccionada')
            print ('Requerimiento de reserva zona 1: %r' % master_instance.REQ_RES_Z1[p].value)
            print ('Requerimiento de reserva zona 2: %r' % master_instance.REQ_RES_Z2[p].value)

    ####  - - - - - - IMPRIMIENDO SI ES NECESARIO  - - - - - - #######

    if master_instance.config_value['debugging_master']:
        print ("--- Exportando LP Master---")
        stdout_ = sys.stdout  # Keep track of the previous value.
        stream = cStringIO.StringIO()
        sys.stdout = stream
        print master_instance.pprint()  # Here you can do whatever you want, import module1, call test
        sys.stdout = stdout_  # restore the previous stdout.
        variable = stream.getvalue()  # This will get the "hello" string inside the variable

        output = open(path_resultados+'modelo_master.txt', 'w')
        output.write(variable)
        master_instance.write(filename=path_resultados+'LP.txt', io_options={'symbolic_solver_labels': True})
        # sys.stdout.write(instance.pprint())
        output.close()

    # Update del despacho encontrado por el maestro, sobre el esclavo
    for g in master_instance.GENERADORES:
        for s in master_instance.ESCENARIOS:
            if master_instance.GEN_UC[g, s].value is None:
                slave_instance.gen_d_uc[g, s] = 0
            else:
                slave_instance.gen_d_uc[g, s] = master_instance.GEN_UC[g, s].value
            slave_instance.gen_d_pg[g, s] = master_instance.GEN_PG[g, s].value
            slave_instance.gen_d_resup[g, s] = master_instance.GEN_PG[g, s].value
    print 'Updating Slave'
    slave_instance.preprocess()
    slave_model.preprocess()
    for g in master_instance.GENERADORES:
            for s in master_instance.ESCENARIOS:
                print slave_instance.CT_forced_pg[g, s].upper
# TODO No funciona el preprocess

    print ("--- Resolviendo la optimizacion del SLAVE---")
    results_slave = opt.solve(slave_instance, tee=True)
    # results.write()
    slave_instance.load(results_slave)

    if slave_instance.Objective_rule()/slave_instance.config_value['voll'] <= GAP_ENS:
        print('Particion optima encontrada: %s' % parti)
        print ('Requerimiento de reserva zona 1: %r' % master_instance.REQ_RES_Z1[parti].value)
        print ('Requerimiento de reserva zona 2: %r' % master_instance.REQ_RES_Z2[parti].value)
        print ('ENS de la particion %r' % slave_instance.Objective_rule.value)
        break
    print ('ENS de la particion: %r [MW]' % (slave_instance.Objective_rule()/slave_instance.config_value['voll']))

    for s in slave_instance.ESCENARIOS:
        for g in slave_instance.GENERADORES:
            print ('Pg ' + g + ', ' + s + ': ' + str(slave_instance.GEN_PG[g, s].value) + ' MW')

    if master_instance.config_value['debugging_slave']:
        print ("--- Exportando LP Slave---")
        stdout_ = sys.stdout  # Keep track of the previous value.
        stream = cStringIO.StringIO()
        sys.stdout = stream
        print slave_instance.pprint()  # Here you can do whatever you want, import module1, call test
        sys.stdout = stdout_  # restore the previous stdout.
        variable = stream.getvalue()  # This will get the "hello" string inside the variable

        output = open(path_resultados+'modelo_slave.txt', 'w')
        output.write(variable)
        master_instance.write(filename=path_resultados+'LP.txt', io_options={'symbolic_solver_labels': True})
        # sys.stdout.write(instance.pprint())
        output.close()

    duales = slave_instance.dual
    master_instance.BENDERS.add(i)
# TODO Agregar corte de benders



print ('\n--------M O D E L O :  "%s"  T E R M I N A D O --------' % master_instance.config_value['scuc'])
print ("path input:" + path_datos + '\n')

# ------R E S U L T A D O S------------------------------------------------------------------------------
print ('------E S C R I B I E N D O --- R E S U L T A D O S------\n')

# Resultados para GENERADORES ---------------------------------------------------
exporter.exportar_gen(master_instance, path_resultados)
# Resultados para LINEAS --------------------------------------------------------
exporter.exportar_lin(master_instance, path_resultados)
# Resultados para BARRAS (ENS)---------------------------------------------------
exporter.exportar_bar(master_instance, path_resultados)
# Resultados del sistema --------------------------------------------------------
exporter.exportar_system(master_instance, path_resultados)
# Resultados de zonas -----------------------------------------------------------
exporter.exportar_zones(master_instance, path_resultados)







