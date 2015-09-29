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


###########################################################################
# PARAMETERS
###########################################################################

# GENERADORES
_model.gen_pmax = Param(_model.GENERADORES)
_model.gen_pmin = Param(_model.GENERADORES)
_model.gen_barra = Param(_model.GENERADORES)
_model.gen_cvar = Param(_model.GENERADORES)
_model.gen_falla = Param(_model.GENERADORES)
_model.gen_rupmax = Param(_model.GENERADORES)
_model.gen_rdnmax = Param(_model.GENERADORES)
_model.gen_cfijo = Param(_model.GENERADORES)
_model.gen_factorcap = Param(_model.GENERADORES)
_model.gen_tipo = Param(_model.GENERADORES)

# LINEAS
_model.linea_fmax = Param(_model.LINEAS)
_model.linea_barA = Param(_model.LINEAS)
_model.linea_barB = Param(_model.LINEAS)
_model.linea_available = Param(_model.LINEAS)
_model.linea_falla = Param(_model.LINEAS)
_model.linea_x = Param(_model.LINEAS)

# BARRAS
_model.demanda = Param(_model.BARRAS)
_model.zona = Param(_model.BARRAS)
_model.vecinos = Param(_model.BARRAS)

# ZONAS
_model.zonal_rup = Param(_model.ZONAS)
_model.zonal_rdn = Param(_model.ZONAS)

# PARAMETROS DE CONFIGURACION; 
# Valores: 1) all (gx y tx), 2) gx (solo gx), 3) tx (solo tx), 4) zonal (reserva por zonas)
_model.config_value = Param(_model.CONFIG)


###########################################################################
# SETS FROM PARAMETERS
###########################################################################
def vecinos_generadores_init(model,g):
    vecinos=[]
    for v in model.vecinos[model.gen_barra[g]]:
        for gg in model.GENERADORES:
            if model.gen_barra[gg]==v and gg!=g:
                vecinos.append(gg)
    return vecinos

_model.VECINOS_GX = Set(_model.GENERADORES, initialize=vecinos_generadores_init)

def falla_scenarios_gx_init(model):
    if model.config_value['scuc'] == 'gx' or model.config_value['scuc'] == 'gx_vecinos' \
        or model.config_value['scuc'] == 'all' :
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

# Unit commitment
_model.GEN_UC = Var(_model.GENERADORES, within=Binary)


# Generacion del generador g, escenario base
def bounds_gen_pg(model, g):
    return 0, model.gen_pmax[g] * model.gen_factorcap[g]
_model.GEN_PG = Var(_model.GENERADORES, within=NonNegativeReals, bounds=bounds_gen_pg)


# Generacion del generador g, Escenarios de falla
def bounds_gen_pg_scenario(model, g, s):
    return 0, model.gen_pmax[g] * model.gen_factorcap[g]
_model.GEN_PG_S = Var(_model.GENERADORES, _model.CONTINGENCIAS,
                     within=NonNegativeReals, bounds=bounds_gen_pg_scenario)

# Reserva UP del generador g, escenario base
def bounds_gen_resup(model, g):
    return 0, model.gen_rupmax[g]
_model.GEN_RESUP = Var(_model.GENERADORES, within=NonNegativeReals, bounds=bounds_gen_resup)


# Reserva DOWN del generador g, escenario base
def bounds_gen_resdn(model, g):
    return 0, model.gen_rdnmax[g]
_model.GEN_RESDN = Var(_model.GENERADORES, within=NonNegativeReals, bounds=bounds_gen_resdn)


# ENS base
def bounds_ens(model, b):
    return 0, model.demanda[b]
_model.ENS = Var(_model.BARRAS, within=NonNegativeReals, bounds=bounds_ens)


# ENS ESCENARIOS
def bounds_ens_scenario(model, b, s):
    return 0, model.demanda[b]
_model.ENS_S = Var(_model.BARRAS, _model.CONTINGENCIAS, within=NonNegativeReals, bounds=bounds_ens_scenario)


# FLUJO MAXIMO LINEAS
def bounds_fmax(model, l):
    if model.linea_available[l]:
        return -model.linea_fmax[l], model.linea_fmax[l]
    else:
        return 0.0,0.0
_model.LIN_FLUJO = Var(_model.LINEAS, bounds=bounds_fmax)


# FLUJO MAXIMO LINEAS SCENARIO
def bounds_fmax_scenario(model, l, s):
    if model.linea_available[l]:
        return -model.linea_fmax[l], model.linea_fmax[l]
    else:
        return 0.0,0.0
_model.LIN_FLUJO_S = Var(_model.LINEAS, _model.CONTINGENCIAS, bounds=bounds_fmax_scenario)


# ANGULO POR BARRAS
def bounds_theta(model, b):
    if b == model.config_value['default_bar']:
        return (0.0,0.0)
    return (-math.pi, math.pi)

_model.THETA = Var(_model.BARRAS, bounds=bounds_theta)


# ANGULO POR BARRAS SCENARIO
def bounds_theta_scenario(model, b, s):
    if b == model.config_value['default_bar']:
        return (0.0,0.0)
    return (-math.pi, math.pi)

_model.THETA_S = Var(_model.BARRAS, _model.CONTINGENCIAS, bounds=bounds_theta_scenario)


###########################################################################
# CONSTRAINTS
###########################################################################

# CONSTRAINT 1: Balance nodal por barra - pre-fault
def nodal_balance_rule(model, b):

    lside = (sum(model.GEN_PG[g] for g in model.GENERADORES if model.gen_barra[g] == b) +
             sum(model.LIN_FLUJO[l] for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
    rside = (model.demanda[b] - model.ENS[b] +
             sum(model.LIN_FLUJO[l] for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))

    return lside == rside

_model.CT_nodal_balance = Constraint(_model.BARRAS, rule=nodal_balance_rule)


# CONSTRAINT 1: Balance nodal por barra - post-fault
def nodal_balance_contingency_rule(model, b, s):
    lside = (sum(model.GEN_PG_S[g, s]
                 for g in model.GENERADORES if model.gen_barra[g] == b and g != s) +
             sum(model.LIN_FLUJO_S[l, s]
                 for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
    rside = (model.demanda[b] - model.ENS_S[b, s] +
             sum(model.LIN_FLUJO_S[l, s]
                 for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))

    return lside == rside

_model.CT_nodal_balance_contingency = Constraint(_model.BARRAS, _model.CONTINGENCIAS,
                                                rule=nodal_balance_contingency_rule)


# CONSTRAINT 2 y 3: Pmin & Pmax - Pre-fault
def p_min_generators_rule(model, g):
    return model.GEN_PG[g] - model.GEN_RESDN[g] >= model.GEN_UC[g] * model.gen_pmin[g] * model.gen_factorcap[g]


def p_max_generators_rule(model, g):
    return model.GEN_PG[g] + model.GEN_RESUP[g] <= model.GEN_UC[g] * model.gen_pmax[g] * model.gen_factorcap[g]

_model.CT_min_power = Constraint(_model.GENERADORES, rule=p_min_generators_rule)

_model.CT_max_power = Constraint(_model.GENERADORES, rule=p_max_generators_rule)


# CONSTRAINT 2 y 3: Pmin & Pmax - Post-fault
def p_min_generators_contingency_rule(model, g, s):
    if g == s:
        return model.GEN_PG_S[g, s] == 0
    if model.config_value['scuc'] == 'gx_vecinos':
        if g in model.VECINOS_GX[s]:
            return model.GEN_PG_S[g, s] >= model.GEN_PG[g] - model.GEN_RESDN[g]
        else:
            return model.GEN_PG_S[g, s] == model.GEN_PG[g]
    else:
        return model.GEN_PG_S[g, s] >= model.GEN_PG[g] - model.GEN_RESDN[g]


def p_max_generators_contingency_rule(model, g, s):
    if g == s:
        return Constraint.Skip
    if model.config_value['scuc'] == 'gx_vecinos':
        if g in model.VECINOS_GX[s]:
            return model.GEN_PG_S[g, s] <= model.GEN_PG[g] + model.GEN_RESUP[g]
        else:
            return Constraint.Skip
    return model.GEN_PG_S[g, s] <= model.GEN_PG[g] + model.GEN_RESUP[g]

_model.CT_min_power_contingency = Constraint(_model.GENERADORES, _model.CONTINGENCIAS,
                                            rule=p_min_generators_contingency_rule)
_model.CT_max_power_contingency = Constraint(_model.GENERADORES, _model.CONTINGENCIAS,
                                            rule=p_max_generators_contingency_rule)


# CONSTRAINT 4: DC Flow - pre-fault
def kirchhoff_rule(model, l):
    rside = model.LIN_FLUJO[l]
    lside = 100 * (model.THETA[model.linea_barB[l]] - model.THETA[model.linea_barA[l]]) / model.linea_x[l]
    return rside == lside

_model.CT_kirchhoff_2nd_law = Constraint(_model.LINEAS, rule=kirchhoff_rule)


# CONSTRAINT 4: DC Flow - post-fault
def kirchhoff_contingency_rule(model, l, s):
    if l == s:
        return model.LIN_FLUJO_S[l, s] == 0
    rside = model.LIN_FLUJO_S[l, s]
    lside = 100 * (model.THETA_S[model.linea_barB[l], s] - model.THETA_S[model.linea_barA[l], s]) / model.linea_x[l]
    return rside == lside

_model.CT_kirchhoff_2nd_law_contingency = Constraint(_model.LINEAS, _model.CONTINGENCIAS,
                                                    rule=kirchhoff_contingency_rule)

# CONSTRAINT 5: RESERVA POR ZONAS
def zonal_reserve_up_rule(model, z):
    if model.config_value['scuc'] == 'none':
        return (sum(model.GEN_RESUP[g] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
                model.zonal_rup[z])
    else:
        return Constraint.Skip


def zonal_reserve_dn_rule(model, z):
    if model.config_value['scuc'] == 'none':
        return (sum(model.GEN_RESDN[g] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
                model.zonal_rdn[z])
    else:
        return Constraint.Skip

_model.CT_zonal_reserve_up = Constraint(_model.ZONAS, rule=zonal_reserve_up_rule)
_model.CT_zonal_reserve_dn = Constraint(_model.ZONAS, rule=zonal_reserve_dn_rule)


###########################################################################
# FUNCION OBJETIVO
###########################################################################

def system_cost_rule(model):
    costo_base = (sum(model.gen_cfijo[g] * model.GEN_UC[g] for g in model.GENERADORES) +
                  sum(model.GEN_PG[g] * model.gen_cvar[g] for g in model.GENERADORES) +
                  sum(model.ENS[b] * model.config_value['voll'] for b in model.BARRAS))

    costo_por_scenario = sum(model.ENS_S[b, s] * model.config_value['voll']
                              for b in model.BARRAS for s in model.CONTINGENCIAS) \
                         #+ sum(model.GEN_PG_S[g, s] * model.gen_cvar[g] for g in model.GENERADORES for s in model.CONTINGENCIAS)
    # (sum(model.gen_cfijo[g] * model.GEN_UC[g] for g in model.GENERADORES) +

    penalizacion_reservas = (sum(0.01 * model.GEN_RESDN[g] for g in model.GENERADORES) +
                             sum(0.01 * model.GEN_RESUP[g] for g in model.GENERADORES))

    return costo_base + costo_por_scenario/(len(model.CONTINGENCIAS)) + penalizacion_reservas


_model.Objective_rule = Objective(rule=system_cost_rule, sense=minimize)
