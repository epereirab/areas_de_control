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
# ZONAS
_model.ZONAS = Set()
# HORAS
_model.ESCENARIOS = Set()


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

# Parametros que provienen del master

_model.gen_d_uc = Param(_model.GENERADORES, _model.ESCENARIOS, mutable=True)
_model.gen_d_pg = Param(_model.GENERADORES, _model.ESCENARIOS, mutable=True)
_model.gen_d_resup = Param(_model.GENERADORES, _model.ESCENARIOS, mutable=True)
_model.req_res1 = Param()
_model.req_res2 = Param()
# _model.gen_d_resdn = Param(_model.GENERADORES, _model.ESCENARIOS)

# LINEAS
_model.linea_fmax = Param(_model.LINEAS)
_model.linea_barA = Param(_model.LINEAS)
_model.linea_barB = Param(_model.LINEAS)
_model.linea_available = Param(_model.LINEAS)
_model.linea_falla = Param(_model.LINEAS)
_model.linea_x = Param(_model.LINEAS)

# BARRAS
_model.demanda = Param(_model.BARRAS, _model.ESCENARIOS)
_model.zona = Param(_model.BARRAS)
_model.vecinos = Param(_model.BARRAS)

# ZONAS
_model.zonal_rup = Param(_model.ZONAS)
_model.zonal_rdn = Param(_model.ZONAS)

# PARAMETROS DE CONFIGURACION; 

_model.config_value = Param(_model.CONFIG)


###########################################################################
# SETS FROM PARAMETERS
###########################################################################
def vecinos_generadores_init(model, g):
    vecinos = []
    for v in model.vecinos[model.gen_barra[g]]:
        for gg in model.GENERADORES:
            if model.gen_barra[gg] == v and gg != g:
                vecinos.append(gg)
    return vecinos

_model.VECINOS_GX = Set(_model.GENERADORES, initialize=vecinos_generadores_init)


def falla_scenarios_gx_init(model):
    if (model.config_value['scuc'] == 'gx' or model.config_value['scuc'] == 'gx_vecinos' or
            model.config_value['scuc'] == 'all'):
        return (g for g in model.GENERADORES if model.gen_falla[g])
    else:
        return []
_model.SCENARIOS_FALLA_GX = Set(initialize=falla_scenarios_gx_init)


def falla_scenarios_tx_init(model):
    if model.config_value['scuc'] == 'tx' or model.config_value['scuc'] == 'all':
        return (l for l in model.LINEAS if model.linea_falla[l])
    else:
        return []
_model.SCENARIOS_FALLA_TX = Set(initialize=falla_scenarios_tx_init)


def fault_scenarios_init(model):
    s = []
    for g in model.SCENARIOS_FALLA_GX:
        s.append(g)
    for l in model.SCENARIOS_FALLA_TX:
        s.append(l)
    return s
_model.CONTINGENCIAS = Set(initialize=fault_scenarios_init)

###########################################################################
# VARIABLES
###########################################################################

# Unit commitment generacion
_model.GEN_UC = Var(_model.GENERADORES, _model.ESCENARIOS,
                    within=Binary)

# Unit commitment reserva
_model.GEN_RES_UC = Var(_model.GENERADORES, _model.ESCENARIOS,
                        within=Binary)


# Generacion del generador g, escenario base
def bounds_gen_pg(model, g, s):
    ub = round(model.gen_pmax[g] * model.gen_factorcap[g, s], 2)
    return 0, ub
_model.GEN_PG = Var(_model.GENERADORES, _model.ESCENARIOS,
                    within=NonNegativeReals, bounds=bounds_gen_pg)


# Generacion del generador g, Escenarios de falla
def bounds_gen_pg_scenario(model, g, s, sf):
    ub = round(model.gen_pmax[g] * model.gen_factorcap[g, s], 2)
    return 0, ub
_model.GEN_PG_S = Var(_model.GENERADORES, _model.ESCENARIOS, _model.CONTINGENCIAS,
                      within=NonNegativeReals, bounds=bounds_gen_pg_scenario)


# Reserva UP del generador g, escenario base
def bounds_gen_resup(model, g, s):
    return 0, model.gen_rupmax[g, s]
_model.GEN_RESUP = Var(_model.GENERADORES, _model.ESCENARIOS,
                       within=NonNegativeReals, bounds=bounds_gen_resup)


# Reserva DOWN del generador g, escenario base
def bounds_gen_resdn(model, g, s):
    return 0, model.gen_rdnmax[g, s]
_model.GEN_RESDN = Var(_model.GENERADORES, _model.ESCENARIOS,
                       within=NonNegativeReals, bounds=bounds_gen_resdn)


# ENS base
def bounds_ens(model, b, s):
    return 0, model.demanda[b, s]
_model.ENS = Var(_model.BARRAS, _model.ESCENARIOS,
                 within=NonNegativeReals, bounds=bounds_ens)


# ENS ESCENARIOS
def bounds_ens_scenario(model, b, s, sf):
    return 0, model.demanda[b, s]
_model.ENS_S = Var(_model.BARRAS, _model.ESCENARIOS, _model.CONTINGENCIAS,
                   within=NonNegativeReals, bounds=bounds_ens_scenario)


# FLUJO MAXIMO LINEAS
def bounds_fmax(model, l, s):
    if model.linea_available[l]:
        return -model.linea_fmax[l], model.linea_fmax[l]
    else:
        return 0.0, 0.0
_model.LIN_FLUJO = Var(_model.LINEAS, _model.ESCENARIOS,
                       bounds=bounds_fmax)


# FLUJO MAXIMO LINEAS SCENARIO
def bounds_fmax_scenario(model, l, s, sf):
    if model.linea_available[l]:
        return -model.linea_fmax[l], model.linea_fmax[l]
    else:
        return 0.0, 0.0
_model.LIN_FLUJO_S = Var(_model.LINEAS, _model.ESCENARIOS, _model.CONTINGENCIAS,
                         bounds=bounds_fmax_scenario)


# ANGULO POR BARRAS
def bounds_theta(model, b, s):
    if b == model.config_value['default_bar']:
        return 0.0, 0.0
    return -math.pi, math.pi

_model.THETA = Var(_model.BARRAS, _model.ESCENARIOS,
                   bounds=bounds_theta)


# ANGULO POR BARRAS SCENARIO
def bounds_theta_scenario(model, b, s, sf):
    if b == model.config_value['default_bar']:
        return 0.0, 0.0
    return -math.pi, math.pi

_model.THETA_S = Var(_model.BARRAS, _model.ESCENARIOS, _model.CONTINGENCIAS,
                     bounds=bounds_theta_scenario)


###########################################################################
# CONSTRAINTS
###########################################################################


# # CONSTRAINT 1: Balance nodal por barra - pre-fault
# def nodal_balance_rule(model, b, s):
#
#     lside = (sum(model.GEN_PG[g, s] for g in model.GENERADORES if model.gen_barra[g] == b) +
#              sum(model.LIN_FLUJO[l, s] for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
#     rside = (model.demanda[b, s] - model.ENS[b, s] +
#              sum(model.LIN_FLUJO[l, s] for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))
#
#     return lside == rside
#
# _model.CT_nodal_balance = Constraint(_model.BARRAS, _model.ESCENARIOS, rule=nodal_balance_rule)


# CONSTRAINT 1: Balance nodal por barra - post-fault
def nodal_balance_contingency_rule(model, b, s, sf):
    lside = (sum(model.GEN_PG_S[g, s, sf]
                 for g in model.GENERADORES if model.gen_barra[g] == b and g != sf) +
             sum(model.LIN_FLUJO_S[l, s, sf]
                 for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
    rside = (model.demanda[b, s] - model.ENS_S[b, s, sf] +
             sum(model.LIN_FLUJO_S[l, s, sf]
                 for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))

    return lside == rside

_model.CT_nodal_balance_contingency = Constraint(_model.BARRAS, _model.ESCENARIOS, _model.CONTINGENCIAS,
                                                 rule=nodal_balance_contingency_rule)


# # CONSTRAINT 2 y 3: Pmin & Pmax - Pre-fault
# def p_min_generators_rule(model, g, s):
#     lb = round(model.gen_pmin[g] * model.gen_factorcap[g, s],2)
#     return (model.GEN_PG[g, s] - model.GEN_RESDN[g, s] >=
#             model.GEN_UC[g, s] * lb)
#
#
# def p_max_generators_rule(model, g, s):
#     ub = round(model.gen_pmax[g] * model.gen_factorcap[g, s],2)
#     return (model.GEN_PG[g, s] + model.GEN_RESUP[g, s] <=
#             model.GEN_UC[g, s] * ub)
#
# _model.CT_min_power = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=p_min_generators_rule)
#
# _model.CT_max_power = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=p_max_generators_rule)


# CONSTRAINT 2 y 3: Pmin & Pmax - Post-fault
def p_min_generators_contingency_rule(model, g, s, sf):
    if g == sf:
        return model.GEN_PG_S[g, s, sf] == 0
    if model.config_value['scuc'] == 'gx_vecinos':
        if g in model.VECINOS_GX[sf]:
            return model.GEN_PG_S[g, s, sf] >= model.GEN_PG[g, s] - model.GEN_RESDN[g, s]
        else:
            return model.GEN_PG_S[g, s, sf] == model.GEN_PG[g, s]
    else:
        return model.GEN_PG_S[g, s, sf] >= model.GEN_PG[g, s] - model.GEN_RESDN[g, s]


def p_max_generators_contingency_rule(model, g, s, sf):
    if g == sf:
        return Constraint.Skip
    if model.config_value['scuc'] == 'gx_vecinos':
        if g in model.VECINOS_GX[sf]:
            return model.GEN_PG_S[g, s, sf] <= model.GEN_PG[g, s] + model.GEN_RESUP[g, s]
        else:
            return Constraint.Skip
    return model.GEN_PG_S[g, s, sf] <= model.GEN_PG[g, s] + model.GEN_RESUP[g, s]

_model.CT_min_power_contingency = Constraint(_model.GENERADORES, _model.ESCENARIOS, _model.CONTINGENCIAS,
                                             rule=p_min_generators_contingency_rule)
_model.CT_max_power_contingency = Constraint(_model.GENERADORES, _model.ESCENARIOS, _model.CONTINGENCIAS,
                                             rule=p_max_generators_contingency_rule)


# # CONSTRAINT 4: DC Flow - pre-fault
# def kirchhoff_rule(model, l, s):
#     rside = model.LIN_FLUJO[l, s]
#     lside = 100 * (model.THETA[model.linea_barB[l], s] - model.THETA[model.linea_barA[l], s]) / model.linea_x[l]
#     return rside == lside
#
# _model.CT_kirchhoff_2nd_law = Constraint(_model.LINEAS, _model.ESCENARIOS, rule=kirchhoff_rule)


# CONSTRAINT 4: DC Flow - post-fault
def kirchhoff_contingency_rule(model, l, s, sf):
    if l == sf:
        return model.LIN_FLUJO_S[l, s, sf] == 0
    rside = model.LIN_FLUJO_S[l, s, sf]
    lside = (100 * (model.THETA_S[model.linea_barB[l], s, sf] - model.THETA_S[model.linea_barA[l], s, sf]) /
             model.linea_x[l])
    return rside == lside

_model.CT_kirchhoff_2nd_law_contingency = Constraint(_model.LINEAS, _model.ESCENARIOS, _model.CONTINGENCIAS,
                                                     rule=kirchhoff_contingency_rule)


# CONSTRAINT 5: RESERVA POR ZONAS
# def zonal_reserve_up_rule(model, z, s):
#     if model.config_value['scuc'] == 'zonal':
#         return (sum(model.GEN_RESUP[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
#                 model.zonal_rup[z])


# def zonal_reserve_dn_rule(model, z, s):
#     if model.config_value['scuc'] == 'zonal':
#         return (sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
#                 model.zonal_rdn[z])
#     if model.config_value['scuc'] == 'zonal_sharing':
#         return (sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) +
#                 sum(model.SHARED_RESDN[z2, z] for z2 in model.ZONAS if not z == z2) >=
#                 model.zonal_rdn[z])
#     else:
#         return Constraint.Skip

# _model.CT_zonal_reserve_up = Constraint(_model.ZONAS, _model.ESCENARIOS, rule=zonal_reserve_up_rule)
# _model.CT_zonal_reserve_dn = Constraint(_model.ZONAS, _model.ESCENARIOS, rule=zonal_reserve_dn_rule)



# FORZANDO DESPACHOS

def forced_pg_rule(model, g, s):
    # if model.config_value['scuc'] == 'forced_scuc':# and round(model.gen_d_uc[g, s],0)>0:
    #     ub = round(model.gen_pmax[g] * model.gen_factorcap[g, s], 2)*round(model.gen_d_uc[g, s], 0)
    #     lb = round(model.gen_pmin[g] * model.gen_factorcap[g, s], 2)*round(model.gen_d_uc[g, s], 0)
    #     if model.gen_d_pg[g, s] > ub or model.gen_d_pg[g, s] < lb:
    #         print "ERROR 1"
    #         print "g_:" + str(g) + " S: " + str(s)
    #
    #     if model.gen_d_resup[g, s] > ub-lb:
    #         return Constraint.Skip
    #         print "ERROR 2"
    #         print "g_:" + str(g) + " S: " + str(s)
    #         print "ub= " + str(ub) + " lb: " + str(lb) + " res " + str(model.gen_d_resup[g, s]) + " resta " + str(ub-lb)
    return model.GEN_PG[g, s] == round(model.gen_d_pg[g, s], 2)
    # else:
    #    return Constraint.Skip

_model.CT_forced_pg = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=forced_pg_rule)


def forced_uc_rule(model, g, s):
    return model.GEN_UC[g, s] == round(model.gen_d_uc[g, s], 0)

_model.CT_forced_uc = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=forced_uc_rule)


def forced_resup_rule(model, g, s):
    return model.GEN_RESUP[g, s] == round(model.gen_d_resup[g, s], 2)

_model.CT_forced_resup = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=forced_resup_rule)


###########################################################################
# FUNCION OBJETIVO
###########################################################################

def system_cost_rule(model):
    security_assesment = sum(model.ENS_S[b, s, sf] * model.config_value['voll']
                             for b in model.BARRAS for s in model.ESCENARIOS for sf in model.CONTINGENCIAS)

    return security_assesment


_model.Objective_rule = Objective(rule=system_cost_rule, sense=minimize)
