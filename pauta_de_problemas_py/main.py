import gurobipy as gp
from gurobipy import GRB
import csv

# Leer los archivos CSV

# Parámetros de cotas superior e inferior para porcentajes de nutrientes
limite_inferior = []
limite_superior = []

with open('limites.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    # Hay que eliminar los títulos
    eliminador = True
    for row in reader:
        if eliminador:
            eliminador = False
        else:
            limite_inferior.append(float(row[0]))
            limite_superior.append(float(row[1]))

n_nutrientes = len(limite_inferior)

# Parámetro de costos de cada cereal

costos = []

with open('costos.csv') as csvfile:
    reader = csv.reader(csvfile)
    # Hay que eliminar los títulos
    eliminador = True
    for row in reader:
        if eliminador:
            eliminador = False
        else:
            costos.append(float(row[0]))

n_cereales = len(costos)



# Matriz de parámetros de porcentaje de nutrientes de cada cereal
# Lista de |n_nutrientes| listas que tienen |n_cereales| elementos.

contenidos = []

with open('contenidos_nutricionales.csv', newline='') as csvfile:
    reader = csv.reader(csvfile, delimiter=',')
    # Hay que eliminar los títulos
    eliminador = True
    for row in reader:
        nutriente = []
        if eliminador:
            eliminador = False
        else:
            for i in range(n_cereales):
                nutriente.append(float(row[i]))
            contenidos.append(nutriente)


# Después de tener los datos se proceda a la implementación del modelo

# Crear el modelo
modelo = gp.Model()

# Crear variables de decisión

x = modelo.addVars(n_cereales, vtype=GRB.CONTINUOUS, name="x")

# Se agrega la no negatividad de las variables

for j in range(n_cereales):
    modelo.addConstr(x[j] >= 0, f"no_negatividad_{j}")

# Se agregan restricciones de proporción mínima de nutrientes
for i in range(n_nutrientes):
    suma_nutriente = sum(contenidos[i][j] * x[j] for j in range(n_cereales))
    modelo.addConstr(suma_nutriente >= limite_inferior[i], f"limite_inferior_{i}")

# Se agregan restricciones de proporción máxima de nutrientes
for i in range(n_nutrientes):
    suma_nutriente = sum(contenidos[i][j] * x[j] for j in range(n_cereales))
    modelo.addConstr(suma_nutriente <= limite_superior[i], f"limite_superior_{i}")

# Se agrega restricción de que la mezcla está hecha solamente por cereales
modelo.addConstr(sum(x[j] for j in range(n_cereales)) == 1, "mezcla_solo_cereales")

# Se define la función objetivo

modelo.setObjective(gp.quicksum(costos[j] * x[j] for j in range(n_cereales)), GRB.MINIMIZE)

# Se resuelve el modelo
modelo.optimize()

# Se imprime la solución
if modelo.status == GRB.OPTIMAL:
    print("Solución óptima encontrada:")
    for cereal in range(n_cereales):
        print(f"Cereal {cereal + 1}: Proporción = {x[cereal].x}")
    print("Costo total:", modelo.objVal, "pesos por cada kilogramo")
else:
    print("No se encontró una solución óptima.")
