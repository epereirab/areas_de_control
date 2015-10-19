import csv


def costo_ens(model):
    """ Costo ENS en estado sin falla """
    return sum(model.ENS[b].value * model.config_value['voll'] for b in model.BARRAS)


def costo_ens_falla(model, sf):
    """ Costo ENS para contingencia sf """
    return sum(model.ENS_S[b, sf].value * model.config_value['voll'] for b in model.BARRAS)


def costo_op(model):
    """ Costo de operacion en estado sin falla """
    return sum(model.GEN_PG[g].value * model.gen_cvar[g] for g in model.GENERADORES)


def costo_op_falla(model, sf):
    """ Costo de operacion para contingencia sf """
    return sum(model.GEN_PG_S[g, sf].value * model.gen_cvar[g] for g in model.GENERADORES)


def costo_base(model):
    """ Costo total (operacion + falla) para estado sin falla """
    return costo_op(model) + costo_ens(model)


def costo_falla(model, sf):
    """ Costo total (operacion + falla) para contingencia sf"""
    return costo_op_falla(model, sf) + costo_ens_falla(model, sf)


def exportar_gen(model, path):
    """ Resultados de Generadores """
    gen = model.GENERADORES
    fallas = model.CONTINGENCIAS
    
    # Resultados para GENERADORES---------------------------------------------------------
    ofile = open(path + 'resultados_generadores.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    ofile2 = open(path + 'resultados_generadores_delta.csv', "wb")
    writer2 = csv.writer(ofile2, delimiter=',', quoting=csv.QUOTE_NONE)
    
    # header
    header = ['Generador', 'barra', 'zona', 'tipo', 'Cvar', 'Pmax',
              'Pmax_eff', 'Pmin', 'UC', 'PG_0', 'RES_UP', 'RES_DN']
    for z in model.ZONAS:
        for s in fallas:
            if z == model.zona[model.gen_barra[s]]:
                if not model.GEN_PG[s] == 0:
                    header.append(str(z) + '-' + str(s))
    writer.writerow(header)
    writer2.writerow(header)
    
    for g in gen:
        tmprow = []
        tmprow.append(g)
        tmprow.append(model.gen_barra[g])
        tmprow.append(model.zona[model.gen_barra[g]])
        tmprow.append(model.gen_tipo[g])
        tmprow.append(model.gen_cvar[g])
        tmprow.append(model.gen_pmax[g])
        tmprow.append(model.gen_pmax[g] * model.gen_factorcap[g])
        tmprow.append(model.gen_pmin[g])
        tmprow.append(model.GEN_UC[g].value)
        tmprow.append(model.GEN_PG[g].value)
        tmprow.append(model.GEN_RESUP[g].value)
        tmprow.append(model.GEN_RESDN[g].value)
        tmprow2 = list(tmprow)
    
        for z in model.ZONAS:
            for s in fallas:
                if z == model.zona[model.gen_barra[s]]:
                    if not model.GEN_PG[s] == 0:
                        tmprow.append(model.GEN_PG_S[g, s].value)
                        if s == g:
                            tmprow2.append('-')
                        else:
                            tmprow2.append(model.GEN_PG_S[g, s].value-model.GEN_PG[g].value)
    
        writer.writerow(tmprow)
        writer2.writerow(tmprow2)

    ofile.close()
    ofile2.close()

    
def exportar_lin(model, path):  
    """ Resultados de Lineas """

    lin = model.LINEAS
    fallas = model.CONTINGENCIAS
    ofile = open(path + 'resultados_lineas.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    tmprow = []
    # header
    header = ['Linea', 'Flujo_MAX', 'Flujo_0']
    for z in model.ZONAS:
        for s in fallas:
            if z == model.zona[model.gen_barra[s]]:
                if not model.GEN_PG[s] == 0:
                    header.append(str(z) + '-' + str(s))
    writer.writerow(header)
    
    for l in lin:
        tmprow.append(l)
        tmprow.append(model.linea_fmax[l])
        tmprow.append(model.LIN_FLUJO[l].value)
        for z in model.ZONAS:
            for s in fallas:
                if z == model.zona[model.gen_barra[s]]:
                    if not model.GEN_PG[s] == 0:
                        tmprow.append(model.LIN_FLUJO_S[l, s].value)
        writer.writerow(tmprow)
        tmprow = []
    
    ofile.close()


def exportar_bar(model, path): 
    """ Resultados de Barras (ENS) """

    bar = model.BARRAS
    fallas = model.CONTINGENCIAS
    
    ofile = open(path + 'resultados_barras.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    tmprow = []
    # header
    header = ['Linea', 'ENS_0']
    for s in fallas:
        header.append('ENS_' + str(s))
    writer.writerow(header)
    
    for b in bar:
        tmprow.append(b)
        tmprow.append(model.ENS[b].value)
    
        for s in fallas:
            tmprow.append(model.ENS_S[b, s].value)
        writer.writerow(tmprow)
        tmprow = []
    
    ofile.close()
    
    
def exportar_system(model, path): 
    """ Resultados de costos del Sistema  """

    fallas = model.CONTINGENCIAS
    
    ofile = open(path + 'resultados_system.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    
    tmprow = []
    # header
    header = ['Valor', '0']
    for s in fallas:
        header.append(str(s))
    writer.writerow(header)
    
    tmprow.append('CostoTotal')
    tmprow.append(costo_base(model))
    for s in fallas:
        tmprow.append(costo_falla(model, s))
    writer.writerow(tmprow)
    tmprow = []
    
    tmprow.append('CostoOperacion')
    tmprow.append(costo_op(model))
    for s in fallas:
        tmprow.append(costo_op_falla(model, s))
    writer.writerow(tmprow)
    tmprow = []
    
    tmprow.append('CostoENS')
    tmprow.append(costo_ens(model))
    for s in fallas:
        tmprow.append(costo_ens_falla(model, s))
    writer.writerow(tmprow)
    tmprow = []
    
    ofile.close()

    
def exportar_zones(model, path): 
    """ Resultados de reserva por Zonas """

    gen = model.GENERADORES
    
    ofile = open(path + 'resultados_zonas.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    tmprow = []
    # header
    header = ['Zona', 'TotalRUP', 'TotalRDN']
    for z in model.ZONAS:
        header.append('RES-TO-ZONE->' + z)
    writer.writerow(header)
    for z in model.ZONAS:
        tmprow.append(str(z))
        tmprow.append(sum(model.GEN_RESUP[g].value for g in gen if model.zona[model.gen_barra[g]] == z))
        tmprow.append(sum(model.GEN_RESDN[g].value for g in gen if model.zona[model.gen_barra[g]] == z))
        if model.config_value['scuc'] == 'zonal_sharing':
            for z2 in model.ZONAS:
                if z == z2:
                    tmprow.append('-')
                else:
                    tmprow.append(model.SHARED_RESUP[z, z2].value)
    
        writer.writerow(tmprow)
        tmprow = []
    
    ofile.close()
