# -*- encoding: utf-8 -*-
#import sys
#import os
#from os.path import abspath, dirname
#sys.path.insert(0, dirname(dirname(dirname(dirname(abspath(__file__))))))
from coopr.pyomo import *
import math
#from pyomo.environ import *
#from coopr.pyomo.base.sparse_indexed_component import *
#SparseIndexedComponent._DEFAULT_INDEX_CHECKING_ENABLED = False

model = AbstractModel()
model.dual = Suffix(direction=Suffix.IMPORT)

###########################################################################
# SETS
###########################################################################


#GENERADORES
model.GENERADORES = Set()
#LINEAS
model.LINEAS = Set()
#BARRAS
model.BARRAS = Set()
#BARRAS
model.CONFIG = Set()


###########################################################################
# PARAMETERS
###########################################################################

#GENERADORES
model.gen_pmax = Param(model.GENERADORES)
model.gen_pmin = Param(model.GENERADORES)
model.gen_barra = Param(model.GENERADORES)
model.gen_cvar = Param(model.GENERADORES)
model.gen_falla = Param(model.GENERADORES)


#LINEAS
model.linea_fmax = Param(model.LINEAS)
model.linea_barA = Param(model.LINEAS)
model.linea_barB = Param(model.LINEAS)
model.linea_available = Param(model.LINEAS)
model.linea_x = Param(model.LINEAS)
#BARRAS
model.demanda = Param(model.BARRAS)

#PARAMETROS DE CONFIGURACION
model.config_value = Param(model.CONFIG)

###########################################################################
# SETS FROM PARAMETERS
###########################################################################
def falla_scenarios_init(model):
    if model.config_value['scuc']:
        return (g for g in model.GENERADORES if model.gen_falla[g])
    else:
        return []
model.SCENARIOS_FALLA_GX = Set(initialize=falla_scenarios_init)

###########################################################################
# VARIABLES
###########################################################################

#Unit commitment
model.GEN_UC = Var(model.GENERADORES, within=Binary)

#generacion del generador g, escenario base
def bounds_gen_pg(model,g):
    return (0,model.gen_pmax[g])

model.GEN_PG = Var(model.GENERADORES, within= NonNegativeReals, bounds = bounds_gen_pg)

#generacion del generador g, Escenarios de falla
def bounds_gen_pg_scenario(model,g, sg):
    if g == sg:
        return (0,0)
    else:
        return (0,model.gen_pmax[g])
model.GEN_PG_S = Var(model.GENERADORES, model.SCENARIOS_FALLA_GX, within= NonNegativeReals, bounds = bounds_gen_pg_scenario)

#ENS base
def bounds_ens(model,b):
    return (0,model.demanda[b])
model.ENS = Var(model.BARRAS, within= NonNegativeReals, bounds = bounds_ens)

def bounds_ens_scenario(model,b, sg):
    return (0,model.demanda[b])
model.ENS_S = Var(model.BARRAS, model.SCENARIOS_FALLA_GX, within= NonNegativeReals, bounds = bounds_ens_scenario)


#FLUJO MAXIMO LINEAS
def bounds_fmax(model,l):
    return (-model.linea_fmax[l],model.linea_fmax[l])
model.LIN_FLUJO = Var(model.LINEAS, bounds = bounds_fmax)

#FLUJO MAXIMO LINEAS SCENARIO
def bounds_fmax_scenario(model,l, sg):
    return (-model.linea_fmax[l],model.linea_fmax[l])
model.LIN_FLUJO_S = Var(model.LINEAS, model.SCENARIOS_FALLA_GX, bounds = bounds_fmax_scenario)


#ANGULO POR BARRAS
model.THETA = Var(model.BARRAS, bounds = (-math.pi, math.pi))

#ANGULO POR BARRAS SCENARIO
model.THETA_S = Var(model.BARRAS, model.SCENARIOS_FALLA_GX, bounds = (-math.pi, math.pi))

###########################################################################
# CONSTRAINTS
###########################################################################


##############   C A S O B A S E  #################
#RESTRICCION 1: abastecimiento de la demanda en cada barra
def balance_demanda_generacion_rule(model,b):
    lside = sum(model.GEN_PG[g] for g in model.GENERADORES if model.gen_barra[g]==b)\
            + sum(model.LIN_FLUJO[l] for l in model.LINEAS if model.linea_barB[l]==b and model.linea_available[l])
    rside = model.demanda[b] - model.ENS[b]+ sum(model.LIN_FLUJO[l] for l in model.LINEAS if model.linea_barA[l]==b  and model.linea_available[l])

    return lside == rside

model.CT_balance_demanda_generacion = Constraint(model.BARRAS, rule=balance_demanda_generacion_rule)

#RESTRICCION 2 y 3: potencias mínima y máxima
def p_min_generadores_rule(model,g):
    return(model.GEN_PG[g] >= model.GEN_UC[g]* model.gen_pmin[g])

def p_max_generadores_rule(model,g):
    return(model.GEN_PG[g] <= model.GEN_UC[g]* model.gen_pmax[g])

model.CT_potencia_minima = Constraint(model.GENERADORES,rule=p_min_generadores_rule)

model.CT_potencia_maxima = Constraint(model.GENERADORES,rule=p_max_generadores_rule)

#RESTRICCION 4: flujo máximo y ángulos por lineas
def l_max_kcof_rule(model,l):
    rside=model.LIN_FLUJO[l]
    lside= 100*(model.THETA[model.linea_barB[l]]-model.THETA[model.linea_barA[l]])/model.linea_x[l]
    return rside == lside

model.CT_lineas_2ley_kcof = Constraint(model.LINEAS,rule=l_max_kcof_rule)


##############   ESCENARIOS DE FALLA  #################
#RESTRICCION 1: abastecimiento de la demanda en cada barra
def balance_demanda_generacion_scen_rule(model,b,sg):

    lside = sum(model.GEN_PG_S[g,sg] for g in model.GENERADORES if model.gen_barra[g]==b and g != sg)\
            + sum(model.LIN_FLUJO_S[l,sg] for l in model.LINEAS if model.linea_barB[l]==b and model.linea_available[l])
    rside = model.demanda[b] - model.ENS_S[b,sg]+ sum(model.LIN_FLUJO_S[l,sg] for l in model.LINEAS if model.linea_barA[l]==b  and model.linea_available[l])

    return lside == rside

model.CT_balance_demanda_generacion_scenario = Constraint(model.BARRAS, model.SCENARIOS_FALLA_GX, rule=balance_demanda_generacion_scen_rule)


#RESTRICCION 2 y 3: potencias mínima y máxima
def p_min_generadores_scen_rule(model,g,sg):
    if g==sg:
        return Constraint.Skip
    return(model.GEN_PG_S[g,sg] >= model.GEN_UC[g]* model.gen_pmin[g])

def p_max_generadores_scen_rule(model,g,sg):
    if g==sg:
        return Constraint.Skip
    return(model.GEN_PG_S[g,sg] <= model.GEN_UC[g]* model.gen_pmax[g])

model.CT_potencia_minima_scenario = Constraint(model.GENERADORES, model.SCENARIOS_FALLA_GX, rule=p_min_generadores_scen_rule)
model.CT_potencia_maxima_scenario = Constraint(model.GENERADORES, model.SCENARIOS_FALLA_GX, rule=p_max_generadores_scen_rule)

#RESTRICCION 4: flujo máximo y ángulos por lineas
def l_max_kcof_scen_rule(model,l,sg):
    rside=model.LIN_FLUJO_S[l,sg]
    lside= 100*(model.THETA_S[model.linea_barB[l],sg]-model.THETA_S[model.linea_barA[l],sg])/model.linea_x[l]
    return rside == lside

model.CT_lineas_2ley_kcof_scenarios = Constraint(model.LINEAS, model.SCENARIOS_FALLA_GX,rule=l_max_kcof_scen_rule)

###########################################################################
# FUNCION OBJETIVO
###########################################################################

def costo_operacion_rule(model):
    costo_base = sum(model.GEN_PG[g]*model.gen_cvar[g] for g in model.GENERADORES)+sum(model.ENS[b]* model.config_value['voll'] for b in model.BARRAS)

    costo_por_scenario = sum(model.GEN_PG_S[g,sg]*model.gen_cvar[g] for g in model.GENERADORES for sg in model.SCENARIOS_FALLA_GX)+sum(model.ENS_S[b,sg]* model.config_value['voll'] for b in model.BARRAS for sg in model.SCENARIOS_FALLA_GX)

    return (costo_base + costo_por_scenario)


model.Objective_rule = Objective(rule=costo_operacion_rule, sense=minimize)
