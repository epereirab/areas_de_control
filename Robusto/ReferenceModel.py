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

#parametros de despacho generadores

_model.gen_d_uc=Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_d_pg=Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_d_resup=Param(_model.GENERADORES, _model.ESCENARIOS)
_model.gen_d_resdn=Param(_model.GENERADORES, _model.ESCENARIOS)

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
# Valores: 1) all (gx y tx), 2) gx (solo gx), 3) tx (solo tx), 4) zonal (reserva por zonas) 5) zonal_sharing 6) forced_scuc
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
    if model.config_value['scuc'] == 'gx' or model.config_value['scuc'] == 'gx_vecinos' or \
                    model.config_value['scuc'] == 'all' or model.config_value['scuc'] == 'forced_scuc':
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


def zonetozone_init(model):
    if model.config_value['scuc'] == 'zonal_sharing':
        return [(z1, z2) for z1 in model.ZONAS for z2 in model.ZONAS if not z1 == z2]
    return []

_model.ZONE2ZONE = Set(dimen=2, initialize=zonetozone_init)


def zones_interconnections_init(model, z1, z2):
    intx = []
    for l in model.LINEAS:
        if model.zona[model.linea_barA[l]] == z1 and model.zona[model.linea_barB[l]] == z2 and model.linea_available[l]:
            intx.append(l)
    return intx

_model.ZONES_INTERCONNECTIONS = Set(_model.ZONE2ZONE, initialize=zones_interconnections_init)

###########################################################################
# VARIABLES
###########################################################################

# Unit commitment generacion
_model.GEN_UC = Var(_model.GENERADORES, _model.ESCENARIOS,
                    within=Binary)

# Unit commitment resreva
_model.GEN_RES_UC = Var(_model.GENERADORES, _model.ESCENARIOS,
                        within=Binary)


# Generacion del generador g, escenario base
def bounds_gen_pg(model, g, s):
    return 0, model.gen_pmax[g] * model.gen_factorcap[g, s]
_model.GEN_PG = Var(_model.GENERADORES, _model.ESCENARIOS,
                    within=NonNegativeReals, bounds=bounds_gen_pg)


# Generacion del generador g, Escenarios de falla
def bounds_gen_pg_scenario(model, g, s, sf):
    return 0, model.gen_pmax[g] * model.gen_factorcap[g, s]
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


# RESERVA COMPARTIDA ENTRE (Z1,Z2), de Z1->Z2
_model.SHARED_RESUP = Var(_model.ZONE2ZONE, within=NonNegativeReals)
_model.SHARED_RESDN = Var(_model.ZONE2ZONE, within=NonNegativeReals)

###########################################################################
# CONSTRAINTS
###########################################################################


# CONSTRAINT 1: Balance nodal por barra - pre-fault
def nodal_balance_rule(model, b, s):

    lside = (sum(model.GEN_PG[g, s] for g in model.GENERADORES if model.gen_barra[g] == b) +
             sum(model.LIN_FLUJO[l, s] for l in model.LINEAS if model.linea_barB[l] == b and model.linea_available[l]))
    rside = (model.demanda[b, s] - model.ENS[b, s] +
             sum(model.LIN_FLUJO[l, s] for l in model.LINEAS if model.linea_barA[l] == b and model.linea_available[l]))

    return lside == rside

_model.CT_nodal_balance = Constraint(_model.BARRAS, _model.ESCENARIOS, rule=nodal_balance_rule)


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


# CONSTRAINT 2 y 3: Pmin & Pmax - Pre-fault
def p_min_generators_rule(model, g, s):
    return (model.GEN_PG[g, s] - model.GEN_RESDN[g, s] >=
            model.GEN_UC[g, s] * model.gen_pmin[g] * model.gen_factorcap[g, s])


def p_max_generators_rule(model, g, s):
    return (model.GEN_PG[g, s] + model.GEN_RESUP[g, s] <=
            model.GEN_UC[g, s] * model.gen_pmax[g] * model.gen_factorcap[g, s])

_model.CT_min_power = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=p_min_generators_rule)

_model.CT_max_power = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=p_max_generators_rule)


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


# CONSTRAINT 4: DC Flow - pre-fault
def kirchhoff_rule(model, l, s):
    rside = model.LIN_FLUJO[l, s]
    lside = 100 * (model.THETA[model.linea_barB[l], s] - model.THETA[model.linea_barA[l], s]) / model.linea_x[l]
    return rside == lside

_model.CT_kirchhoff_2nd_law = Constraint(_model.LINEAS, _model.ESCENARIOS, rule=kirchhoff_rule)


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
def zonal_reserve_up_rule(model, z, s):
    if model.config_value['scuc'] == 'none':
        return (sum(model.GEN_RESUP[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
                model.zonal_rup[z])
    if model.config_value['scuc'] == 'zonal_sharing':
        return (sum(model.GEN_RESUP[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) +
                sum(model.SHARED_RESUP[z2, z] for z2 in model.ZONAS if not z == z2) >=
                model.zonal_rup[z])
    else:
        return Constraint.Skip


def zonal_reserve_dn_rule(model, z, s):
    if model.config_value['scuc'] == 'none':
        return (sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
                model.zonal_rdn[z])
    if model.config_value['scuc'] == 'zonal_sharing':
        return (sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) +
                sum(model.SHARED_RESDN[z2, z] for z2 in model.ZONAS if not z == z2) >=
                model.zonal_rdn[z])
    else:
        return Constraint.Skip

_model.CT_zonal_reserve_up = Constraint(_model.ZONAS, _model.ESCENARIOS, rule=zonal_reserve_up_rule)
_model.CT_zonal_reserve_dn = Constraint(_model.ZONAS, _model.ESCENARIOS, rule=zonal_reserve_dn_rule)


# CONSTRAINT 6: SHARING RESERVE CONSTRAINT
def sharing_resup_rule(model, z, z2, s):
    if model.config_value['scuc'] == 'zonal_sharing':
        return (model.SHARED_RESUP[z, z2] <=
                sum(model.GEN_RESUP[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z))
    else:
        return Constraint.Skip


def sharing_resdn_rule(model, z, z2, s):
    if z == z2:
        return Constraint.Skip
    if model.config_value['scuc'] == 'zonal_sharing':
        return (model.SHARED_RESDN[z, z2] <=
                sum(model.GEN_RESDN[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z))
    else:
        return Constraint.Skip

_model.CT_sharing_resup = Constraint(_model.ZONE2ZONE, _model.ESCENARIOS, rule=sharing_resup_rule)
_model.CT_sharing_resdn = Constraint(_model.ZONE2ZONE, _model.ESCENARIOS, rule=sharing_resdn_rule)


# CONSTRAINT 7: MAX SHARED RESERVE TO MAX FLOW INTERCONNECTION
def max_shared_resup_rule(model, z, z2, s):
    if model.config_value['scuc'] == 'zonal_sharing':
        return (model.SHARED_RESUP[z, z2] <=
                sum((model.linea_fmax[l] - model.LIN_FLUJO[l, s]) for l in model.ZONES_INTERCONNECTIONS[z, z2]) +
                sum((model.linea_fmax[l] + model.LIN_FLUJO[l, s]) for l in model.ZONES_INTERCONNECTIONS[z2, z]))
    else:
        return Constraint.Skip


def max_shared_resdn_rule(model, z, z2, s):
    if model.config_value['scuc'] == 'zonal_sharing':
        return (model.SHARED_RESDN[z, z2] <=
                sum((model.linea_fmax[l] + model.LIN_FLUJO[l, s]) for l in model.ZONES_INTERCONNECTIONS[z, z2]) +
                sum((model.linea_fmax[l] - model.LIN_FLUJO[l, s]) for l in model.ZONES_INTERCONNECTIONS[z2, z]))
    else:
        return Constraint.Skip

_model.CT_max_shared_resup = Constraint(_model.ZONE2ZONE, _model.ESCENARIOS, rule=max_shared_resup_rule)
_model.CT_max_shared_resdn = Constraint(_model.ZONE2ZONE, _model.ESCENARIOS, rule=max_shared_resdn_rule)


# CONSTRAINT 8: RESERVA MINIMA y MAXIMA (modelos Zonales)
def min_reserve_up(model, g, s):
    if model.config_value['scuc'] == 'zonal_sharing' or model.config_value['scuc'] == 'none':
        return model.GEN_RESUP[g, s] >= model.GEN_RES_UC[g, s] * model.config_value['rup_min']
    else:
        return Constraint.Skip


def max_reserve_up(model, g, s):
    if model.config_value['scuc'] == 'zonal_sharing' or model.config_value['scuc'] == 'none':
        return model.GEN_RESUP[g, s] <= model.GEN_RES_UC[g, s] * model.gen_rupmax[g, s]
    else:
        return Constraint.Skip

_model.CT_max_reserve_up = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=max_reserve_up)
_model.CT_min_reserve_up = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=min_reserve_up)


# CONSTRAINT 8: CANTIDAD MINIMA DE GENERADORES APORTANDO RESERVA
def min_reserve_gen_number(model, z, s):
    if model.config_value['scuc'] == 'zonal_sharing' or model.config_value['scuc'] == 'none':
        return (sum(model.GEN_RES_UC[g, s] for g in model.GENERADORES if model.zona[model.gen_barra[g]] == z) >=
                model.config_value['ngen_min'])
    else:
        return Constraint.Skip

_model.CT_min_reserve_gen_number = Constraint(_model.ZONAS, _model.ESCENARIOS, rule=min_reserve_gen_number)

#Forzando despachos

def forced_pg_rule(model, g, s):
    if model.config_value['scuc'] == 'forced_scuc':
        return model.GEN_PG[g, s] == model.gen_d_pg[g,s]
    else:
        return Constraint.Skip

_model.CT_forced_pg = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=forced_pg_rule)

def forced_uc_rule(model, g, s):
    if model.config_value['scuc'] == 'forced_scuc':
        return model.GEN_UC[g, s] == model.gen_d_uc[g,s]
    else:
        return Constraint.Skip

_model.CT_forced_uc = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=forced_uc_rule)

def forced_resup_rule(model, g, s):
    if model.config_value['scuc'] == 'forced_scuc':
        return model.GEN_RESUP[g, s] == model.gen_d_resup[g,s]
    else:
        return Constraint.Skip

_model.CT_forced_resup = Constraint(_model.GENERADORES, _model.ESCENARIOS, rule=forced_resup_rule)
###########################################################################
# FUNCION OBJETIVO
###########################################################################

def system_cost_rule(model):
    costo_base = (sum(model.gen_cfijo[g] * model.GEN_UC[g, s] for g in model.GENERADORES for s in model.ESCENARIOS) +
                  sum(model.GEN_PG[g, s] * model.gen_cvar[g, s] for g in model.GENERADORES for s in model.ESCENARIOS) +
                  sum(model.ENS[b, s] * model.config_value['voll'] for b in model.BARRAS for s in model.ESCENARIOS))

    costo_por_scenario = sum(model.ENS_S[b, s, sf] * model.config_value['voll']
                             for b in model.BARRAS for s in model.ESCENARIOS for sf in model.CONTINGENCIAS)
    # + sum(model.GEN_PG_S[g, s] * model.gen_cvar[g] for g in model.GENERADORES for s in model.CONTINGENCIAS)
    # (sum(model.gen_cfijo[g] * model.GEN_UC[g] for g in model.GENERADORES) +

    penalizacion_reservas = (sum(0.01 * model.GEN_RESDN[g, s] for g in model.GENERADORES for s in model.ESCENARIOS) +
                             sum(0.01 * model.GEN_RESUP[g, s] for g in model.GENERADORES for s in model.ESCENARIOS))

    return costo_base + costo_por_scenario + penalizacion_reservas


_model.Objective_rule = Objective(rule=system_cost_rule, sense=minimize)
