import csv


def costo_ens(model, s):
    """ Costo ENS en estado sin falla, para un escenario s"""
    return sum(model.ENS[b, s].value * model.config_value['voll'] for b in model.BARRAS)


def costo_ens_escenario_falla(model, s, sf):
    """ Costo ENS para contingencia sf, para un escenario s"""
    return sum(model.ENS_S[b, s, sf].value * model.config_value['voll'] for b in model.BARRAS)


def costo_op(model, s):
    """ Costo de operacion en estado sin falla, para un escenario s"""
    return sum(model.GEN_PG[g, s].value * model.gen_cvar[g, s] for g in model.GENERADORES)


def costo_op_escenario_falla(model, s, sf):
    """ Costo de operacion para contingencia sf, para un escenario s"""
    return sum(model.GEN_PG_S[g, s, sf].value * model.gen_cvar[g, s] for g in model.GENERADORES)


def costo_base(model, s):
    """ Costo total (operacion + falla) para estado sin falla en escenario s """
    return costo_op(model, s) + costo_ens(model, s)


def costo_escenario_falla(model, s, sc):
    """ Costo total (operacion + falla) para contingencia sc en escenario s """
    return costo_op_escenario_falla(model, s, sc) + costo_ens_escenario_falla(model, s, sc)


def exportar_gen(model, path):
    """ Resultados de Generadores """
    gen = model.GENERADORES
    fallas = model.CONTINGENCIAS
    scen = model.ESCENARIOS
    
    # Resultados para GENERADORES---------------------------------------------------------
    ofile = open(path + 'resultados_generadores.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    ofile2 = open(path + 'resultados_generadores_delta.csv', "wb")
    writer2 = csv.writer(ofile2, delimiter=',', quoting=csv.QUOTE_NONE)

    # header
    header = ['Generador', 'Escenario', 'zona', 'barra', 'tipo', 'Cvar', 'Pmin', 'Pmax', 'Pmax_eff', 'UC',
              'PG_0', 'RES_UP', 'RES_DN']
    for sf in fallas:
        header.append(model.gen_barra[sf] + '-' + str(sf))
    writer.writerow(header)
    writer2.writerow(header)

    for s in scen:
        for g in gen:
            tmprow = []
            tmprow.append(g)
            tmprow.append(s)
            tmprow.append(model.zona[model.gen_barra[g]])
            tmprow.append(model.gen_barra[g])
            tmprow.append(model.gen_tipo[g])
            tmprow.append(model.gen_cvar[g, s])
            tmprow.append(model.gen_pmin[g])
            tmprow.append(model.gen_pmax[g])
            tmprow.append(model.gen_pmax[g] * model.gen_factorcap[g, s])
            tmprow.append(0 if str(model.GEN_UC[g, s].value) == 'None' else model.GEN_UC[g, s].value)
            tmprow.append(model.GEN_PG[g, s].value)
            tmprow.append(model.GEN_RESUP[g, s].value)
            tmprow.append(model.GEN_RESDN[g, s].value)
            tmprow2 = list(tmprow)

            for sf in fallas:
                tmprow.append(model.GEN_PG_S[g, s, sf].value)
                if sf == g:
                    tmprow2.append('-')
                else:
                    tmprow2.append(model.GEN_PG_S[g, s, sf].value-model.GEN_PG[g, s].value)

            writer.writerow(tmprow)
            writer2.writerow(tmprow2)

    ofile.close()
    ofile2.close()
    
    
def exportar_lin(model, path):  
    """ Resultados de Lineas """

    lin = model.LINEAS
    fallas = model.CONTINGENCIAS
    scen = model.ESCENARIOS
    
    ofile = open(path + 'resultados_lineas.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    tmprow = []
    # header
    header = ['Linea', 'Escenario', 'Flujo_MAX', 'Flujo_0']
    for sf in fallas:
        header.append(str(model.gen_barra[sf]) + '-' + str(sf))
    writer.writerow(header)

    for s in scen:
        for l in lin:
            tmprow.append(l)
            tmprow.append(s)
            tmprow.append(model.linea_fmax[l])
            tmprow.append(model.LIN_FLUJO[l, s].value)
            for sf in fallas:
                tmprow.append(model.LIN_FLUJO_S[l, s, sf].value)
            writer.writerow(tmprow)
            tmprow = []
    
    ofile.close()


def exportar_bar(model, path): 
    """ Resultados de Barras (ENS) """

    bar = model.BARRAS
    fallas = model.CONTINGENCIAS
    scen = model.ESCENARIOS

    ofile = open(path + 'resultados_barras.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    tmprow = []
    # header
    header = ['Barra', 'Escenario', 'ENS_0']
    for sf in fallas:
        header.append(model.gen_barra[sf] + 'ENS_' + str(sf))
    writer.writerow(header)

    for s in scen:
        for b in bar:
            tmprow.append(b)
            tmprow.append(s)
            tmprow.append(model.ENS[b, s].value)
            for sf in fallas:
                tmprow.append(model.ENS_S[b, s, sf].value)
            writer.writerow(tmprow)
            tmprow = []
    
    ofile.close()
    
    
def exportar_system(model, path): 
    """ Resultados de costos del Sistema  """

    fallas = model.CONTINGENCIAS
    scen = model.ESCENARIOS

    ofile = open(path + 'resultados_system.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

    # Header
    header = ['Valor', 'Escenario', '0']
    for sf in fallas:
        header.append(model.gen_barra[sf] + '-' + str(sf))
    writer.writerow(header)

    for s in scen:
        tmprow = []
        tmprow.append('CostoTotal')
        tmprow.append(costo_base(model, s))
        for sf in fallas:
            tmprow.append(costo_escenario_falla(model, s, sf))
        writer.writerow(tmprow)

        tmprow = []
        tmprow.append('CostoOperacion')
        tmprow.append(costo_op(model, s))
        for sf in fallas:
            tmprow.append(costo_op_escenario_falla(model, s, sf))
        writer.writerow(tmprow)

        tmprow = []
        tmprow.append('CostoENS')
        tmprow.append(costo_ens(model, s))
        for sf in fallas:
            tmprow.append(costo_ens_escenario_falla(model, s, sf))
        writer.writerow(tmprow)
    
    ofile.close()
    
    
def exportar_zones(model, path): 
    """ Resultados de reserva por Zonas """

    gen = model.GENERADORES
    scen = model.ESCENARIOS

    ofile = open(path + 'resultados_zonas.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

    # Header
    header = ['Zona', 'Escenario', 'TotalRUP', 'TotalRDN']
    if model.config_value['scuc'] == 'zonal_sharing':
        for z in model.ZONAS:
            header.append('RES-TO-ZONE->' + z)
    writer.writerow(header)
    for s in scen:
        for z in model.ZONAS:
            tmprow = []
            tmprow.append(str(z))
            tmprow.append(s)
            tmprow.append(sum(model.GEN_RESUP[g, s].value for g in gen if model.zona[model.gen_barra[g]] == z))
            tmprow.append(sum(model.GEN_RESDN[g, s].value for g in gen if model.zona[model.gen_barra[g]] == z))
            if model.config_value['scuc'] == 'zonal_sharing':
                for z2 in model.ZONAS:
                    if z == z2:
                        tmprow.append('-')
                    else:
                        tmprow.append(model.SHARED_RESUP[z, z2].value)

            writer.writerow(tmprow)
    
    ofile.close()
