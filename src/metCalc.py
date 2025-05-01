def find_esat(tair, p0):
    a0 = 3.53624e-4
    a1 = 2.9328363e-5
    a2 = 2.6168979e-7
    a3 = 8.5813609e-9
    b0 = -1.07588e1
    b1 = 6.3268134e-2
    b2 = -2.5368934e-4
    b3 = 6.3405286e-7
    g0 = -2.8365744e3
    g1 = -6.028076559e3
    g2 = 1.954263612e1
    g3 = -2.737830188e-2
    g4 = 1.6261698e-5
    g5 = 7.0229056e-10
    g6 = -1.8680009e-13
    g7 = 2.7150305
    # Conversión de la temperatura de °C a K
    tair = tair + 273.15
    import math
    esat = 0.01 * math.exp((g0 * math.pow(tair,-2)) + g1 * math.pow(tair,-1) + g2 + g3 * tair + g4 * math.pow(tair,2) + g5 * math.pow(tair,3) + g6 * math.pow(tair,4) + g7 * math.log(tair))
     # Conversión de la temperatura de K a °C
    tair = tair - 273.15
    alfa = a0 + a1 * tair + a2 * math.pow(tair,2) + a3 * math.pow(tair,3) 
    beta = math.exp(b0 + b1 * tair + b2 * math.pow(tair,2) + b3 * math.pow(tair,3))
    enhace = math.exp(alfa * (1 - esat/p0) + beta * (p0/esat - 1))
    return enhace * esat
def find_evapor_tw(tair, twet, p0, psic, esat_wet):
    return esat_wet - psic * p0 * (tair - twet)
def find_td(evapor):
    c0 = 2.0798233e2
    c1 = -2.0156028e1
    c2 = 4.6778925e-1
    c3 = -9.2288067e-6
    d0 = 1
    d1 = -0.13319669
    d2 = 5.6577518e-3
    d3 = -7.5172865e-5
    import math
    evapor_ln = math.log(100*evapor)
    return (c0 + c1 * evapor_ln + c2 * math.pow(evapor_ln,2) + c3 * math.pow(evapor_ln,3)) / (d0 + d1 * evapor_ln + d2 * math.pow(evapor_ln,2) + d3 * math.pow(evapor_ln,3)) - 273.15
def find_twet(tair, p0, psic, evapor):
    twet_aux = tair
    evapor_aux = evapor + 0.1
    while evapor_aux > evapor:
        esat_wet_aux = find_esat(twet_aux,p0)
        evapor_aux = find_evapor_tw(tair,twet_aux,p0,psic,esat_wet_aux)
        twet_aux = twet_aux - 0.1
    return twet_aux
def find_evapor_tdew(tdew):
    import math
    return 6.1078 * math.pow(10, 7.5 * tdew / (tdew + 237.3))
def find_r(evapor, p0):
    # epsilon es la relación molar
    epsilon = 0.62198
    return epsilon * evapor / (p0 - evapor)
def find_hspec(r):
    return r / (1 + r)
def find_tv(tair,r):
    # epsilon es la relación molar
    epsilon = 0.62198
    return 0.9995 * (tair * (1 + (r / epsilon)) / (1 + r))
def find_density(tv, p0):
    # constante del aire seco
    rair_dry = 2.87053e2
    return 100 * p0 / (rair_dry * (tv + 273.15))
def find_habs(density,hspec):
    return density * hspec
def find_hr(evapor, esat):
    return 100 * evapor / esat
def find_evapor_hr(esat, hr):
    return 0.01 * hr * esat
def find_deficit(esat,evapor):
    return esat - evapor
def find_heat_index(tair, hr):
    import math
    # conversión de °C a °F
    tair_f = 1.8 * tair + 32
    if tair_f < 40:
        return (tair_f - 32) / 1.8
    else:
        a = -10.3 + 1.1 * tair_f + 0.047 * hr
        if a < 79:
            return (a - 32) / 1.8
        else:
            b = -42.379 + 2.04901523 * tair_f + 10.14333127 * hr - 0.22475541 * tair_f * hr - 0.00683783 * math.pow(tair_f ,2) - 0.054817117 * math.pow(hr,2) + 0.00122874 * math.pow(tair_f,2) * hr + 0.00085282 * tair_f * math.pow(hr,2) - 0.00000199 * math.pow(hr,2) * math.pow(tair_f,2)
            if (hr <= 13 and (tair_f >= 80 and tair_f <= 112)):
                return ((b - 0.25 * (13 - hr) * math.sqrt((17 - abs(tair_f - 95)) / 17)) - 32) / 1.8
            else:
                if (hr > 85 and (tair_f >= 80 and tair_f <= 87)):
                    return  ((b + 0.02 * (hr - 85) * (87 - tair_f)) - 32) / 1.8
                else:
                    return (b - 32) / 1.8
def find_g(lat, h):
    # función que calcula la aceleración local de la gravedad, a una altura h, en m/s^2
    # lat = latitud local, en décimas de °
    import math
    lat_rad = math.radians(lat)
    result = 9.780327 * (1 + 5.3024e-3 * math.pow(math.sin(lat_rad),2) - 5.8e-6 * math.pow(math.sin(2 * lat_rad),2))
    # Valor teórico de la gravedad local en la latitud y al nivel medio del mar
    result = round(result - 3.086e-6 * h,5)
    # Valor teórico de la gravedad local en la latitud y a la altura h
    # Fórmula recomendada hasta una altura de 10 km
    return result
def find_hp(lat, h, g):
    # función que calcula la altura geopotencial local hp, en mgp
    # h = altura local, en m
    # g = aceleración local de la gravedad al nivel medio del mar, en m/s^2
    import math
    lat_rad = math.radians(lat)
    result = round(h * (g - 0.5 * h * (3.0855e-6 + 2.27e-9 * math.cos(2 * lat_rad))) / 9.80665,2)
    return result
def find_p0(hbar, p):
    tm = 25.5   # tm = temperatura media anual en Cuba, en °C
    result = round(p + (34.68 * hbar / (tm + 273.15)),1)
    return result
def find_corr_bar(corr_inst, tbar, p0, g):
    # función que calcula la corrección del barómetro de mercurio, en hPa
    # corr_inst = corrección instrumental del certificado de calibración, en hPa
    # tbar = temperatura del barómetro, en °C
    # p0 = lectura de presión de la escala del barómetro, en hPa
    gn = 9.80665 # aceleración normal de la gravedad, en m/s^2 
    result = -1.63e-4 * p0 * tbar - 4.4e-3 * (tbar - 20)                # corrección de la escala por temperatura
    result = round(result + p0 * (g - gn) / gn + 0.1 + corr_inst, 1)    # corrección de la escala por gravedad y 0.1 hPa por altura del instrumento
    return result
def find_pnm(tair, tair_12, evapor, hp, p0):
    # función que calcula la presión al nivel medio del mar, en hPa
    # tair = temperatura del aire, en °C
    # ev = presión de vapor del agua, en hPa
    # hp = altura geopotencial de la estación, en mgp
    # p0 = presión al nivel de la estación, en hPa
    a = 6.5e-3          # a = gradiente vertical de temperatura en la columna de aire ficticia entre el nivel del mar y el nivel de la estación, en K/mgp
    kp = 1.48275e-2     # kp = constante hipsométrica K/mgp
    ch = 0.10740 + 2.30991e-5 * hp - 7.80886e-10 * hp**2  + 5.12821e-12 * hp**3 - 2.331e-15 * hp**4     # ch = factor de corrección de humedad, en K/hPa
    tv = 0.5 * (tair + tair_12) + 273.15 + 0.5 * a * hp + evapor * ch           # tv = temperatura virtual del aire al nivel medio del mar
    result = round(p0 * 10 ** (kp * hp / tv),1)
    return result
def find_h850(tair, tair_12, evapor, hp, p0):
    # función que calcula la altura de la isobara de 850 hPa, en mgp
    # tair = temperatura del aire, en °C
    # ev = presión de vapor del agua, en hPa
    # hp = altura geopotencial de la estación, en mgp
    # p0 = presión al nivel de la estación, en hPa
    import math
    a = 6.5e-3      # gradiente vertical de temperatura en la columna de aire entre el nivel de la estación y el nivel de 850 hPa, K/m
    kp = 1.48275e-2 # kp = constante hipsométrica K/mgp
    ch = 0.10740 + 2.30991e-5 * hp - 7.80886e-10 * hp**2  + 5.12821e-12 * hp**3 - 2.331e-15 * hp**4     # ch = factor de corrección de humedad, en K/hPa
    tv = 0.5 * (tair + tair_12) + 273.15 + evapor * ch
    if hp < 850:
        result = round(hp - (tv * math.log10(850/p0)) / (kp - 0.5 * a * math.log10(850/p0)),1)
    else:
        result = round(hp + (tv * math.log10(p0/850)) / (kp + 0.5 * a * math.log10(p0/850)),1)
    return result