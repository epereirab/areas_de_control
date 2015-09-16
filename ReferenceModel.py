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

model = AbstractModel()
model.dual = Suffix(direction=Suffix.IMPORT)

###########################################################################
# SETS
###########################################################################


# GENERADORES
model.GENERADORES = Set()
# LINEAS
model.LINEAS = Set()
# BARRAS
model.BARRAS = Set()
# BARRAS
model.CONFIG = Set()


###########################################################################
# PARAMETERS
###########################################################################

# GENERADORES
model.gen_pmax = Param(model.GENERADORES)
model.gen_pmin = Param(model.GENERADORES)
model.gen_barra = Param(model.GENERADORES)
model.gen_cvar = Param(model.GENERADORES)
model.gen_falla = Param(model.GENERADORES)
model.gen_rupmax = Param(model.GENERADORES)
model.gen_rdnmax = Param(model.GENERADORES)

# LINEAS
model.linea_fmax = Param(model.LINEAS)
model.linea_barA = Param(model.LINEAS)
model.linea_barB = Param(model.LINEAS)
model.linea_available = Param(model.LINEAS)
model.linea_falla = Param(model.LINEAS)
model.linea_x = Param(model.LINEAS)

# BARRAS
model.demanda = Param(model.BARRAS)

# PARAMETROS DE CONFIGURACION
model.config_value = Param(model.CONFIG)


###########################################################################
# SETS FROM PARAMETERS
###########################################################################

def falla_scenarios_gx_init(model):
    if model.config_value['scuc']:
        return (g for g in model.GENERADORES if model.gen_falla[g])
    else:
        return []
model.SCENARIOS_FALLA_GX = Set(initialize=falla_scenarios_gx_init)


def falla_scenarios_tx_init(model):
    if model.config_value['scuc']:
        return (l for l in model.LINEAS if model.linea_falla[l])
    else:
        return []
model.SCENARIOS_FALLA_TX = Set(initialize=falla_scenarios_tx_init)


def fault_scenarios_init(model):
    s = []
    for g in model.SCENARIOS_FALLA_GX:
        s.append(g)
    for l in model.SCENARIOS_FALLA_TX:
        s.append(l)
    return s
model.CONTINGENCIAS = Set(initialize=fault_scenarios_init)

###########################################################################
# VARIABLES
###########################################################################

# Unit commitment
model.GEN_UC = Var(model.GENERADORES, within=Binary)


# Generacion del generador g, escenario base
def bounds_gen_pg(model, g):
    return 0, model.gen_pmax[g]
model.GEN_PG = Var(model.GENERADORES, within=NonNegativeReals, bounds=bounds_gen_pg)


# Generacion del generador g, Escenarios de falla
def bounds_gen_pg_scenario(model, g, s):
    if g == s:
        return 0, 0
    else:
        return 0, model.gen_pmax[g]
model.GEN_PG_S = Var(model.GENERADORES, model.CONTINGENCIAS,
                     within=NonNegativeReals, bounds=bounds_gen_pg_scenario)


# Reserva UP del generador g, escenario base
def bounds_gen_resup(model, g):
    return 0, model.gen_rupmax[g]
model.GEN_RESUP = Var(model.GENERADORES, within=NonNegativeReals, bounds=bounds_gen_resup)


# Reserva DOWN del generador g, escenario base
def bounds_gen_resdn(model, g):
    return 0, model.gen_rdnmax[g]
model.GEN_RESDN = Var(model.GENERADORES, within=NonNegativeReals, bounds=bounds_gen_resdn)


# ENS base
def bounds_ens(model, b):
    return 0, model.demanda[b]
model.ENS = Var(model.BARRAS, within=NonNegativeReals, bounds=bounds_ens)


# ENS ESCENARIOS
def bounds_ens_scenario(model, b, s):
    return 0, model.demanda[b]
model.ENS_S = Var(model.BARRAS, model.CONTINGENCIAS, within=NonNegativeReals, bounds=bounds_ens_scenario)


# FLUJO MAXIMO LINEAS
def bounds_fmax(model, l):
    return -model.linea_fmax[l], model.linea_fmax[l]
model.LIN_FLUJO = Var(model.LINEAS, bounds=bounds_fmax)


# FLUJO MAXIMO LINEAS SCENARIO
def bounds_fmax_scenario(model, l, s):
    if l == s:
        return 0, 0
    else:
        return -model.linea_fmax[l], model.linea_fmax[l]
model.LIN_FLUJO_S = Var(model.LINEAS, model.CONTINGENCIAS, bounds=bounds_fmax_scenario)


# ANGULO POR BARRAS
model.THETA = Var(model.BARRAS, bounds=(-math.pi, math.pi))

# ANGULO POR BARRAS SCENARIO
model.THETA_S = Var(model.BARRAS, model.CONTINGENCIAS, bounds=(-math.pi, math.pi))

###########################################################################
# CONSTRAINTS
###########################################################################


# CONSTRAINT 0: Barra de referencia
def reference_bar_rule(model):
    for b in model.BARRAS:
        if b == model.config_value['default_bar']:
            return model.THETA[b] == 0
model.CT_reference_bar = Constraint(rule=reference_bar_rule)


def reference_bar_rule_contingency(model, s):
    return sum(model.THETA_S[b, s] for b in model.BARRAS if b == model.config_value['default_bar']) == 0.0
model.CT_reference_bar_contingency = Constraint(model.CONTINGENCIAS, rule=reference_bar_rule_contingency)

# CONSTRAINT 1: Balance nodal por barra - pre-fault
def nodal_balance_rule(model, b):
    lside = (sum(model.GEN_PG[g] for g in model.GENERADORES if model.gen_barra[g] == b) +
             sum(model.LIN_FLUJO[l] for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
    rside = (model.demanda[b] - model.ENS[b] +
             sum(model.LIN_FLUJO[l] for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))

    return lside == rside

model.CT_nodal_balance = Constraint(model.BARRAS, rule=nodal_balance_rule)


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

model.CT_nodal_balance_contingency = Constraint(model.BARRAS, model.CONTINGENCIAS,
                                                rule=nodal_balance_contingency_rule)


# CONSTRAINT 2 y 3: Pmin & Pmax - Pre-fault
def p_min_generators_rule(model, g):
    return model.GEN_PG[g] - model.GEN_RESDN[g] >= model.GEN_UC[g] * model.gen_pmin[g]


def p_max_generators_rule(model, g):
    return model.GEN_PG[g] + model.GEN_RESUP[g] <= model.GEN_UC[g] * model.gen_pmax[g]

model.CT_min_power = Constraint(model.GENERADORES, rule=p_min_generators_rule)

model.CT_max_power = Constraint(model.GENERADORES, rule=p_max_generators_rule)


# CONSTRAINT 2 y 3: Pmin & Pmax - Post-fault
def p_min_generators_contingency_rule(model, g, s):
    if g == s:
        return Constraint.Skip
    return model.GEN_PG_S[g, s] >= model.GEN_PG[g] - model.GEN_RESDN[g]


def p_max_generators_contingency_rule(model, g, s):
    if g == s:
        return Constraint.Skip
    return model.GEN_PG_S[g, s] <= model.GEN_PG[g] + model.GEN_RESUP[g]

model.CT_min_power_contingency = Constraint(model.GENERADORES, model.CONTINGENCIAS,
                                            rule=p_min_generators_contingency_rule)
model.CT_max_power_contingency = Constraint(model.GENERADORES, model.CONTINGENCIAS,
                                            rule=p_max_generators_contingency_rule)


# CONSTRAINT 4: DC Flow - pre-fault
def kirchhoff_rule(model, l):
    rside = model.LIN_FLUJO[l]
    lside = 100 * (model.THETA[model.linea_barB[l]] - model.THETA[model.linea_barA[l]]) / model.linea_x[l]
    return rside == lside

model.CT_kirchhoff_2nd_law = Constraint(model.LINEAS, rule=kirchhoff_rule)


# CONSTRAINT 4: DC Flow - post-fault
def kirchhoff_contingency_rule(model, l, s):
    if l == s:
        return Constraint.Skip
    rside = model.LIN_FLUJO_S[l, s]
    lside = 100 * (model.THETA_S[model.linea_barB[l], s] - model.THETA_S[model.linea_barA[l], s]) / model.linea_x[l]
    return rside == lside

model.CT_kirchhoff_2nd_law_contingency = Constraint(model.LINEAS, model.CONTINGENCIAS,
                                                    rule=kirchhoff_contingency_rule)


# CONSTRAINT 5: NO ENS in intact system
# def bah(model, b):
#     return model.ENS[b] == 0
#
# model.CT_noENS = Constraint(model.BARRAS, rule=bah)


###########################################################################
# FUNCION OBJETIVO
###########################################################################

def system_cost_rule(model):
    costo_base = (sum(model.GEN_PG[g] * model.gen_cvar[g] for g in model.GENERADORES) +
                  sum(model.ENS[b] * model.config_value['voll'] for b in model.BARRAS))

    costo_por_scenario = (sum(model.GEN_PG_S[g, s] * model.gen_cvar[g]
                              for g in model.GENERADORES for s in model.CONTINGENCIAS) +
                          sum(model.ENS_S[b, s] * model.config_value['voll']
                              for b in model.BARRAS for s in model.CONTINGENCIAS))

    return costo_base + costo_por_scenario


model.Objective_rule = Objective(rule=system_cost_rule, sense=minimize)
