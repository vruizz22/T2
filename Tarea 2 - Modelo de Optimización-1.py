import gurobipy as gp
from gurobipy import GRB, Model, quicksum
import pandas as pd
import csv

# 1. Sección de Datos
# 1.1 Extraer datos:
with open('cantidad_cuadrantes.csv', 'r') as f: #k
    reader = csv.reader(f)
    cantidad_cuadrantes = [int(row[0]) for row in reader]

with open('capacidad_por_saco.csv', 'r') as f: #Alpha
    reader = csv.reader(f)
    capacidad_por_saco = [int(row[0]) for row in reader]

with open('capital_inicial.csv', 'r') as f: #Gamma
    reader = csv.reader(f)
    capital_inicial = [int(row[0]) for row in reader]
    
with open('costo_saco.csv', 'r') as f: #Charlie
    reader = csv.reader(f)
    costo_saco = [[int(x) for x in row] for row in reader]

with open('kilos_fruta.csv', 'r') as f: #Lambda
    reader = csv.reader(f)
    kilos_fruta = [int(row[0]) for row in reader]

with open('precio_venta.csv', 'r') as f: #Beta
    reader = csv.reader(f)
    precio_venta = [[int(x) for x in row] for row in reader]
    
with open('tiempo_demora.csv', 'r') as f: #Theta
    reader = csv.reader(f)
    tiempo_demora = [int(row[0]) for row in reader]
    
# 1.2 Declarar conjuntos y parametros:
J = len(kilos_fruta)
K = cantidad_cuadrantes[0]
T = len(costo_saco[0])
h = 0 #ESTO ES LO QUE ESTOY CAMBIANDO

# 2. Sección de modelación

# 2.1 Generar el modelo:
modelo = gp.Model('Implementación computacional')

# 2.2 Definir variables:
x = modelo.addVars(J,K,T, vtype=GRB.BINARY, name="x")
y = modelo.addVars(J,K,T, vtype=GRB.BINARY, name="y")
i = modelo.addVars(T, vtype=GRB.CONTINUOUS, name="I")
u = modelo.addVars(J,T, vtype=GRB.INTEGER, name="U")
w = modelo.addVars(J,T, vtype=GRB.INTEGER, name="W")

# 2.3 Incorporar variables al modelo:
modelo.update()

# 2.4 Generar restricciones:

# 2.4.1 Restricción de activación de sembrado y solo un sembrado por cuadrante
for j in range(J):
    for k in range(K):
        for t in range(T):
            modelo.addConstr(quicksum(y[j, k, l] for l in range(t, min(t + tiempo_demora[j]-h, T))) >= tiempo_demora[j] * x[j, k, t], name="Activacion_sembrado") #QUITE EL -1 por h
            
for k in range(K):
    for t in range(T):
        modelo.addConstr(quicksum(y[j, k, t] for j in range(J)) <= 1, name="Solo_un_sembrado_por_cuadrante")
                
# 2.4.2 Restricción de inventario de dinero y condición borde inventario dinero
for t in range(1, T):
    modelo.addConstr(i[t] == i[t-1] - quicksum(costo_saco[j][t] * w[j, t] for j in range(J)) +
                     quicksum(quicksum(x[j, k, t - tiempo_demora[j]] * kilos_fruta[j] * precio_venta[j][t] for k in range(K) if t - tiempo_demora[j] >= h) for j in range(J)), name="Inventario_dinero") #QUITE EL -1 por h
        
modelo.addConstr(i[0] == capital_inicial[0] - quicksum(costo_saco[j][0] * w[j, 0] for j in range(J)), name="Condicion_borde_inventario_dinero")

# 2.4.3 Restricción inventario semillas y condición borde inventario semilla
for j in range(J):
    for t in range(1, T):
        modelo.addConstr(u[j, t] == u[j, t-1] + capacidad_por_saco[j] * w[j, t] - quicksum(x[j, k, t] for k in range(K)), name="Inventario_semilla")
        
    modelo.addConstr(u[j, 0] == capacidad_por_saco[j] * w[j, 0] - quicksum(x[j, k, 0] for k in range(K)), name="Condicion_borde_inventario_semilla")

# 2.4.4 Restricción de terminar cosecha antes de volver a cosechar
for j in range(J):
    for k in range(K):
        for t in range(T-1):
            modelo.addConstr(1 - x[j, k, t] >= quicksum(x[j, k, l] for l in range(t + 1, min(t + tiempo_demora[j]-h, T))), "Terminar_cosecha_antes_de_volver_a_cosechar") #QUITE EL -1 por h

# 2.4.5 Restricción naturaleza de variables
for t in range(T):
    modelo.addConstr(i[t]>= 0, "Capital positivo")
    
for j in range(J):
    for t in range(T):
        modelo.addConstr(u[j,t]>= 0, "Cantidad de semillas positiva")
        modelo.addConstr(w[j,t]>= 0, "Cantidad de sacos positiva")

# 2.5 Generar función objetivo:
modelo.setObjective(i[T-1], GRB.MAXIMIZE)

# 2.6 Generar optimización:
modelo.optimize()

# 2.7 Visualizar soluciones:
# 2.7.1 Función para imprimir los resultados con detalles de cada terreno mes a mes
def print_results(modelo, x, J, K, T, tiempo_demora):
    print("\n"+"-"*9+"Valor óptimo:"+"-"*9)
    print(f"Valor óptimo: {int(modelo.ObjVal)} Unidades monetarias")
    print("\n"+"-"*9+"Cantidad de veces que se plantó en cada terreno:"+"-"*9)
    for k in range(K):
        count = sum(1 for t in range(T) for j in range(J) if x[j, k, t].x > 0.5)
        print(f"Terreno {k + 1}: {count} veces")
    
    print("\n"+"-"*9+"Detalle de cada terreno mes a mes:"+"-"*9)
    for k in range(K):
        print(f"Terreno {k + 1}:")
        for t in range(T):
            planted = False
            for j in range(J):
                if x[j, k, t].x > 0.5:
                    print(f"Mes {t+1}: Se plantó la semilla {j+1} con un tiempo de demora de {tiempo_demora[j]} meses")
                    planted = True
            if not planted:
                print(f"Mes {t+1}: No se plantó ninguna semilla")
        print("\n")

# 2.7.2 Función para generar y guardar la tabla como CSV con detalles de cada terreno mes a mes
def generar_tabla_csv(modelo, x, J, K, T, tiempo_demora):
    # Crear una matriz vacía
    calendario = [[0 for _ in range(T)] for _ in range(K)]
    
    # Rellenar la matriz con los valores de las semillas
    for j in range(J):
        for k in range(K):
            for t in range(T):
                if x[j, k, t].x > 0.5:
                    calendario[k][t] = j + 1
    
    # Convertir la matriz a un DataFrame de pandas
    df_calendario = pd.DataFrame(calendario, columns=[f'Mes {t+1}' for t in range(T)], index=[f'Terreno {k+1}' for k in range(K)])
    
    # Guardar el DataFrame como un archivo CSV
    df_calendario.to_csv('calendario_plantaciones.csv', index=True)
    print("\nTabla de calendario guardada en la carpeta como 'calendario_plantaciones.csv' con detalles de cada terreno mes a mes.")

# 2.7.3 Función para generar y mostrar la tabla en la consola con detalles de cada terreno mes a mes
def mostrar_tabla_consola(modelo, x, J, K, T, tiempo_demora):
    # Crear una matriz vacía
    calendario = [[0 for _ in range(T)] for _ in range(K)]
    
    # Rellenar la matriz con los valores de las semillas
    for j in range(J):
        for k in range(K):
            for t in range(T):
                if x[j, k, t].x > 0.5:
                    calendario[k][t] = j + 1
    
    # Convertir la matriz a un DataFrame de pandas
    df_calendario = pd.DataFrame(calendario, columns=[f'Mes {t+1}' for t in range(T)], index=[f'Terreno {k+1}' for k in range(K)])
    
    # Mostrar el DataFrame en la consola

# Llamar a las funciones después de resolver el modelo
print_results(modelo, x, J, K, T, tiempo_demora)
mostrar_tabla_consola(modelo, x, J, K, T, tiempo_demora)
generar_tabla_csv(modelo, x, J, K, T, tiempo_demora)

