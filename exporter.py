import csv


def costo_ENS(instance):
    return sum(instance.ENS[b].value * instance.config_value['voll'] for b in instance.BARRAS)

def costo_ENS_escenario(instance,sc):
    return sum(instance.ENS_S[b, sc].value * instance.config_value['voll'] for b in instance.BARRAS)

def costo_op(instance):
    return sum(instance.GEN_PG[g].value * instance.gen_cvar[g] for g in instance.GENERADORES)

def costo_op_escenario(instance,sc):
    return sum(instance.GEN_PG_S[g, sc].value * instance.gen_cvar[g] for g in instance.GENERADORES)

def costo_base(instance):
    return costo_op(instance) + costo_ENS(instance)

def costo_escenario(instance,sc):
    return costo_op_escenario(instance,sc) + costo_ENS_escenario(instance,sc)

def exportar_gen(instance, path_resultados):
    """ Resultados de Generadores """

    gen = instance.GENERADORES
    scen = instance.CONTINGENCIAS
    lin = instance.LINEAS
    bar = instance.BARRAS

    # Resultados para GENERADORES---------------------------------------------------------
    ofile = open(path_resultados + 'resultados_generadores.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

    ofile2 = open(path_resultados + 'resultados_generadores_delta.csv', "wb")
    writer2 = csv.writer(ofile2, delimiter=',', quoting=csv.QUOTE_NONE)

    tmprow = []
    tmprow2 = []
    # header
    header = ['Generador', 'barra', 'zona', 'tipo', 'Cvar', 'Pmax', 'Pmax_eff', 'Pmin', 'UC', 'PG_0', 'RES_UP', 'RES_DN']
    for z in instance.ZONAS:
        for s in scen:
            if z == instance.zona[instance.gen_barra[s]]:
                if not instance.GEN_PG[s] == 0:
                    header.append(str(z) + '-' + str(s))
    writer.writerow(header)
    writer2.writerow(header)

    for g in gen:
        tmprow.append(g)
        tmprow.append(instance.gen_barra[g])
        tmprow.append(instance.zona[instance.gen_barra[g]])
        tmprow.append(instance.gen_tipo[g])
        tmprow.append(instance.gen_cvar[g])
        tmprow.append(instance.gen_pmax[g])
        tmprow.append(instance.gen_pmax[g] * instance.gen_factorcap[g])
        tmprow.append(instance.gen_pmin[g])
        tmprow.append(instance.GEN_UC[g].value)
        tmprow.append(instance.GEN_PG[g].value)
        tmprow.append(instance.GEN_RESUP[g].value)
        tmprow.append(instance.GEN_RESDN[g].value)
        tmprow2 = list(tmprow)

        for z in instance.ZONAS:
            for s in scen:
                if z == instance.zona[instance.gen_barra[s]]:
                    if not instance.GEN_PG[s] == 0:
                        tmprow.append(instance.GEN_PG_S[g, s].value)
                        if s == g:
                            tmprow2.append('-')
                        else:
                            tmprow2.append(instance.GEN_PG_S[g, s].value-instance.GEN_PG[g].value)

        writer.writerow(tmprow)
        writer2.writerow(tmprow2)
        tmprow = []
        tmprow2 = []
    ofile.close()
    ofile2.close()
    

def exportar_lin(instance, path_resultados):
    """ Resultados de Lineas """
    lin = instance.LINEAS
    scen = instance.CONTINGENCIAS
    ofile = open(path_resultados + 'resultados_lineas.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

    tmprow = []
    # header
    header = ['Linea', 'Flujo_MAX', 'Flujo_0']
    for z in instance.ZONAS:
        for s in scen:
            if z == instance.zona[instance.gen_barra[s]]:
                if not instance.GEN_PG[s] == 0:
                    header.append(str(z) + '-' + str(s))
    writer.writerow(header)

    for l in lin:
        tmprow.append(l)
        tmprow.append(instance.linea_fmax[l])
        tmprow.append(instance.LIN_FLUJO[l].value)
        for z in instance.ZONAS:
            for s in scen:
                if z == instance.zona[instance.gen_barra[s]]:
                    if not instance.GEN_PG[s] == 0:
                        tmprow.append(instance.LIN_FLUJO_S[l, s].value)
        writer.writerow(tmprow)
        tmprow = []

    ofile.close()


def exportar_bar(instance, path_resultados):
    """ Resultados de Barras (ENS) """

    scen = instance.CONTINGENCIAS

    bar = instance.BARRAS
    ofile = open(path_resultados + 'resultados_barras.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

    tmprow = []
    # header
    header = ['Linea', 'ENS_0']
    for s in scen:
        header.append('ENS_' + str(s))
    writer.writerow(header)

    for b in bar:
        tmprow.append(b)
        tmprow.append(instance.ENS[b].value)

        for s in scen:
            tmprow.append(instance.ENS_S[b, s].value)
        writer.writerow(tmprow)
        tmprow = []

    ofile.close()
    

def exportar_system(instance, path_resultados):
    """ Resultados de costos del Sistema  """
    gen = instance.GENERADORES
    scen = instance.CONTINGENCIAS
    lin = instance.LINEAS
    bar = instance.BARRAS
    ofile = open(path_resultados + 'resultados_system.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)

    tmprow = []
    # header
    header = ['Valor', 'BASE']
    for s in scen:
        header.append(str(s))
    writer.writerow(header)

    tmprow.append('CostoTotal')
    tmprow.append(costo_base(instance))
    for s in scen:
        tmprow.append(costo_escenario(instance,s))
    writer.writerow(tmprow)
    tmprow = []

    tmprow.append('CostoOperacion')
    tmprow.append(costo_op(instance))
    for s in scen:
        tmprow.append(costo_op_escenario(instance,s))
    writer.writerow(tmprow)
    tmprow = []

    tmprow.append('CostoENS')
    tmprow.append(costo_ENS(instance))
    for s in scen:
        tmprow.append(costo_ENS_escenario(instance,s))
    writer.writerow(tmprow)
    tmprow = []

    ofile.close()
    

def exportar_zones(instance, path_resultados):
    """ Resultados de reserva por Zonas """

    gen = instance.GENERADORES

    ofile = open(path_resultados + 'resultados_zonas.csv', "wb")
    writer = csv.writer(ofile, delimiter=',', quoting=csv.QUOTE_NONE)
    tmprow = []
    # header
    header = ['Zona', 'TotalRUP', 'TotalRDN']
    for z in instance.ZONAS:
        header.append('RES-TO-ZONE->' + z)
    writer.writerow(header)
    for z in instance.ZONAS:
        tmprow.append(str(z))
        tmprow.append(sum(instance.GEN_RESUP[g].value for g in gen if instance.zona[instance.gen_barra[g]] == z))
        tmprow.append(sum(instance.GEN_RESDN[g].value for g in gen if instance.zona[instance.gen_barra[g]] == z))
        if instance.config_value['scuc'] == 'zonal_sharing':
            for z2 in instance.ZONAS:
                if z == z2:
                    tmprow.append('-')
                else:
                    tmprow.append(instance.SHARED_RESUP[z, z2].value)

        writer.writerow(tmprow)
        tmprow = []

    ofile.close()
