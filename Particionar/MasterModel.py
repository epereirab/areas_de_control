# -*- encoding: utf-8 -*-
# import sys
# import os
# from os.path import abspath, dirname
# sys.path.insert(0, dirname(dirname(dirname(dirname(abspath(__file__))))))
from coopr.pyomo import *
import math
# from pyomo.environ import *
# from coopr.pyomo.base.sparse_indexed_component import *
# SparseIndexedComponent._DEFAULT_INDEX_CHECKING_ENABLED = False

_model = AbstractModel()
_model.dual = Suffix(direction=Suffix.IMPORT)

###########################################################################
# SETS
###########################################################################


# GENERADORES
_model.GENERADORES = Set()
# LINEAS
_model.LINEAS = Set()
# BARRAS
_model.BARRAS = Set()
# BARRAS
_model.CONFIG = Set()
# HORAS
_model.ESCENARIOS = Set()
# PARTICIONES
_model.PARTICIONES = Set()
# ZONAS
_model.ZONAS = Set()
# CORTES DE BENDERS
_model.BENDERS = Set(within=PositiveIntegers, ordered=True)

###########################################################################
# PARAMETERS
###########################################################################

# GENERADORES
_model.gen_pmax = Param(_model.GENERADORES)
_model.gen_pmin = Param(_model.GENERADORES)
_model.gen_barra = Param(_model.GENERADORES)
_model.gen_cvar = Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_falla = Param(_model.GENERADORES)
_model.gen_rupmax = Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_rdnmax = Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_cfijo = Param(_model.GENERADORES)
_model.gen_factorcap = Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_tipo = Param(_model.GENERADORES)


# LINEAS
_model.linea_fmax = Param(_model.LINEAS)
_model.linea_barA = Param(_model.LINEAS)
_model.linea_barB = Param(_model.LINEAS)
_model.linea_available = Param(_model.LINEAS)
_model.linea_falla = Param(_model.LINEAS)
_model.linea_x = Param(_model.LINEAS)

# BARRAS
_model.demanda = Param(_model.BARRAS, _model.ESCENARIOS)

_model.vecinos = Param(_model.BARRAS)

# PARTICIONES
_model.barras_zona1 = Param(_model.PARTICIONES)
_model.barras_zona2 = Param(_model.PARTICIONES)

# PARAMETROS DE CONFIGURACION; 
# Nzonas = Numero de zonas a usar
# c_res = valor de penalizacion de reserva

_model.config_value = Param(_model.CONFIG)

# Parametros de cortes de benders
_model.dual_req1 = Param(_model.BENDERS)
_model.dual_req2 = Param(_model.BENDERS)


#TODO Hacerlo para un numero N de zonas a usar
###########################################################################
# SETS FROM PARAMETERS
###########################################################################
# def zonas_particiones(model, g):
#     zonas = []
#     for i in range(1,model.config_value['Nzonas']):
#         zonas.append(i)
# _model.ZONAS_DE_PARTICIONES = Set(_model.PARTICIONES, initialize=zonas_particiones)

###########################################################################
# PARAMETERS FROM PARAMETERS
###########################################################################
# Zona (barra, particion)
def zonasporparticion(model, b, p):
    for bt in model.barras_zona1[p]:
        if bt == b:
            return 1
    for bt in model.barras_zona2[p]:
        if bt == b:
            return 2
    return 0

_model.zona = Param(_model.BARRAS, _model.PARTICIONES,
                    initialize=zonasporparticion)
###########################################################################
# VARIABLES
###########################################################################

# Unit commitment generacion
_model.GEN_UC = Var(_model.GENERADORES, _model.ESCENARIOS,
                    within=Binary)

# Unit commitment reserva
_model.GEN_RES_UC = Var(_model.GENERADORES, _model.ESCENARIOS,
                        within=Binary)


# Generacion del generador g
def bounds_gen_pg(model, g, s):
    ub = round(model.gen_pmax[g] * model.gen_factorcap[g, s],2)
    return 0, ub
_model.GEN_PG = Var(_model.GENERADORES, _model.ESCENARIOS,
                    within=NonNegativeReals, bounds=bounds_gen_pg)


# Reserva UP del generador g
def bounds_gen_resup(model, g, s):
    return 0, model.gen_rupmax[g, s]
_model.GEN_RESUP = Var(_model.GENERADORES, _model.ESCENARIOS,
                       within=NonNegativeReals, bounds=bounds_gen_resup)


# Reserva DOWN del generador g
def bounds_gen_resdn(model, g, s):
    return 0, model.gen_rdnmax[g, s]
_model.GEN_RESDN = Var(_model.GENERADORES, _model.ESCENARIOS,
                       within=NonNegativeReals, bounds=bounds_gen_resdn)


# ENS base
def bounds_ens(model, b, s):
    return 0, model.demanda[b, s]
_model.ENS = Var(_model.BARRAS, _model.ESCENARIOS,
                 within=NonNegativeReals, bounds=bounds_ens)


# FLUJO MAXIMO LINEAS
def bounds_fmax(model, l, s):
    if model.linea_available[l]:
        return -model.linea_fmax[l], model.linea_fmax[l]
    else:
        return 0.0, 0.0
_model.LIN_FLUJO = Var(_model.LINEAS, _model.ESCENARIOS,
                       bounds=bounds_fmax)


# ANGULO POR BARRAS
def bounds_theta(model, b, s):
    if b == model.config_value['default_bar']:
        return 0.0, 0.0
    return -math.pi, math.pi

_model.THETA = Var(_model.BARRAS, _model.ESCENARIOS,
                   bounds=bounds_theta)

# REQUERIMIENTOS DE RESERVA POR ZONA Y PARTICION

_model.REQ_RES_Z1 = Var(_model.PARTICIONES,
                        within=NonNegativeReals)
_model.REQ_RES_Z2 = Var(_model.PARTICIONES,
                        within=NonNegativeReals)

# COMMITMENT DE PARTICION
_model.C_PART = Var(_model.PARTICIONES, within=Binary)

# FUNCION OBJETIVO DEL ESCLAVO, EVALUACION DE SEGURIDAD
_model.SLAVE_SECURITY = Var(within=NonNegativeReals)


###########################################################################
# CONSTRAINTS
###########################################################################


# CONSTRAINT 1: Balance nodal por barra
def nodal_balance_rule(model, b, s):

    lside = (sum(model.GEN_PG[g, s] for g in model.GENERADORES if model.gen_barra[g] == b) +
             sum(model.LIN_FLUJO[l, s] for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
    rside = (model.demanda[b, s] - model.ENS[b, s] +
             sum(model.LIN_FLUJO[l, s] for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))

    return lside == rside

_model.CT_nodal_balance = Constraint(_model.BARRAS, _model.ESCENARIOS, rule=nodal_balance_rule)


# CONSTRAINT 2 y 3: Pmin & Pmax
def p_min_generators_rule(model, g, s):
    lb = round(model.gen_pmin[g] * model.gen_factorcap[g, s],2)
    return (model.GEN_PG[g, s] - model.GEN_RESDN[g, s] >=
            model.GEN_UC[g, s] * lb)


def p_max_generators_rule(model, g, s):
    ub = round(model.gen_pmax[g] * model.gen_factorcap[g, s],2)
    return (model.GEN_PG[g, s] + model.GEN_RESUP[g, s] <=
            model.GEN_UC[g, s] * ub)

_model.CT_min_power = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=p_min_generators_rule)

_model.CT_max_power = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=p_max_generators_rule)


# CONSTRAINT 4: DC Flow
def kirchhoff_rule(model, l, s):
    rside = model.LIN_FLUJO[l, s]
    lside = 100 * (model.THETA[model.linea_barB[l], s] - model.THETA[model.linea_barA[l], s]) / model.linea_x[l]
    return rside == lside

_model.CT_kirchhoff_2nd_law = Constraint(_model.LINEAS, _model.ESCENARIOS, rule=kirchhoff_rule)


# CONSTRAINT 5: RESERVA POR ZONAS
def zonal_reserve_up_rule_z1(model, s, p):
    return (sum(model.GEN_RESUP[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g], p] == 1) >=
            model.REQ_RES_Z1[p] - (1-model.C_PART[p])*100000)


def zonal_reserve_up_rule_z2(model, s, p):
    return (sum(model.GEN_RESUP[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g], p] == 2) >=
            model.REQ_RES_Z2[p] - (1-model.C_PART[p])*100000)


# def zonal_reserve_dn_rule_z1(model, s, p):
#     return (sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g], p] == 1) >=
#             model.zonal_rdn[z])
#
#
# def zonal_reserve_dn_rule_z2(model, s, p):
#     return (sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g], p] == 2) >=
#             model.zonal_rdn[z])

_model.CT_zonal_reserve_up_Z1 = Constraint(_model.ESCENARIOS, _model.PARTICIONES, rule=zonal_reserve_up_rule_z1)
_model.CT_zonal_reserve_up_Z2 = Constraint(_model.ESCENARIOS, _model.PARTICIONES, rule=zonal_reserve_up_rule_z2)
# _model.CT_zonal_reserve_dn_z = Constraint(_model.ESCENARIOS, _model.PARTICIONES, rule=zonal_reserve_dn_rule_z1)
# _model.CT_zonal_reserve_dn_Z2 = Constraint(_model.ESCENARIOS, _model.PARTICIONES, rule=zonal_reserve_dn_rule_z2)


# CONSTRAINT 6: SELECCION DE 1 SOLA PARTICION
def partition_selection(model):
    return sum(model.C_PART[p] for p in model.PARTICIONES) == 1

_model.CT_partition_selection = Constraint(rule=partition_selection)


# CONSTRAINT 7: CANTIDAD MINIMA DE GENERADORES APORTANDO RESERVA
def min_reserve_gen_number(model, z, s):
    return (sum(model.GEN_RES_UC[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
            model.config_value['ngen_min'])

_model.CT_min_reserve_gen_number = Constraint(_model.ZONAS, _model.ESCENARIOS, rule=min_reserve_gen_number)


# CONSTRAINT 8: RESERVA MINIMA y MAXIMA
def min_reserve_up(model, g, s):
    if model.config_value['scuc'] == 'zonal_sharing' or model.config_value['scuc'] == 'zonal':
        return model.GEN_RESUP[g, s] >= model.GEN_RES_UC[g, s] * model.config_value['rup_min']
    else:
        return Constraint.Skip


def max_reserve_up(model, g, s):
    if model.config_value['scuc'] == 'zonal_sharing' or model.config_value['scuc'] == 'zonal':
        return model.GEN_RESUP[g, s] <= model.GEN_RES_UC[g, s] * model.gen_rupmax[g, s]
    else:
        return Constraint.Skip

_model.CT_max_reserve_up = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=max_reserve_up)
_model.CT_min_reserve_up = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=min_reserve_up)

# CONSTRAINT 8: CORTES DE BENDERS de REQUERIMIENTOS DE RESERVA

_model.CT_benders_reserve_requirement = ConstraintList()


###########################################################################
# FUNCION OBJETIVO
###########################################################################

def system_cost_rule(model):
    costo_base = (sum(model.gen_cfijo[g] * model.GEN_UC[g, s] for g in model.GENERADORES for s in model.ESCENARIOS) +
                  sum(model.GEN_PG[g, s] * model.gen_cvar[g, s] for g in model.GENERADORES for s in model.ESCENARIOS) +
                  sum(model.ENS[b, s] * model.config_value['voll'] for b in model.BARRAS for s in model.ESCENARIOS))


    penalizacion_reservas = (sum(model.config_value['c_res'] * model.GEN_RESDN[g, s]
                                 for g in model.GENERADORES for s in model.ESCENARIOS) +
                             sum(model.config_value['c_res'] * model.GEN_RESUP[g, s]
                                 for g in model.GENERADORES for s in model.ESCENARIOS))

    return costo_base + penalizacion_reservas + model.SLAVE_SECURITY


_model.Objective_rule = Objective(rule=system_cost_rule, sense=minimize)
