from gurobipy import (GRB, Model, quicksum)
import gurobipy as gp

'''
La implementacion computacional de este problema debe poder recibir cualquier instancia de par´ametros,
independiente de su tamano y valores de los dato

No puede asumir valores ni cardinalidades de ningun
parametro o conjunto

los cuadrantes como los tipos de semillas seran trabajados de manera
abstracta, solo considerandolos por sus indices


Se usaran archivos de disntitntos valores y dimensiones
para testear el codigo.

Los archivos csv indicaran los tamaños de los conjuntos
K J T. TODOS LOS VALORES SERAN ENTEROS

Todos parten en 1 y terminan en la cardinalidad del conjutno


capacidad por saco:

Archivo de 1 sola columa y J filas.
Contiene la info de del parametro a_j


'''




class Modelo:
    
    def __init__(self) -> None:
        # Leer los archivos
        
        with open('limites.csv', 'r') as limites:
            limites_header = limites.readline().split(',')
            self.limites = [line.strip().split(',') for line in limites.readlines()]
            self.largo_limites = len(self.limites)
        
        with open('costos.csv', 'r') as costos:
            costos_header = costos.readline()
            self.costos = [costo.strip() for costo in costos.readlines()]
            
        with open('contenidos_nutricionales.csv', 'r') as contenidos:
            self.contenidos_header = contenidos.readline().strip().split(',')
            self.contenidos = [line.strip().split(',') for line in contenidos.readlines()]
            # Definicion de parametros:
            self.J = {cereal: costo for cereal, costo in zip(self.contenidos_header, self.costos)}            
            self.I = {i+1: (self.limites[i][0], self.limites[i][1]) for i in range(len(self.limites))}
            
        self.a_ij = {i + 1: {self.contenidos_header[j]: self.contenidos[i][j] for j in range(len(self.J))} for i in range(len(self.I))}

    def implementar_modelo(self) -> tuple:
        # Implementando el modelo
        model = gp.Model()
        
        # Variables
        x_j = model.addVars(self.J, vtype=GRB.CONTINUOUS, name="x_j")
        
        # Agregamos las variables al modelo
        model.update()
        
        # Restricciones
        '''
        1. La mezcla esta compuesta unicamente por cereales
        2. Se debe cumplir una proporcion minima de nutrientes
        3. Se debe cunokir una proporcion máxima de nutrientes
        Naturaleza de Variables
        x_j >= 0
        '''
        model.addConstr(quicksum(x_j[j] for j in self.J.keys()) == 1, name="R1")
        model.addConstrs((quicksum(float(self.a_ij[i][j]) * x_j[j] for j in self.J) >= float(self.I[i][0]) for i in self.I), name="R2")
        model.addConstrs((quicksum(float(self.a_ij[i][j]) * x_j[j] for j in self.J) <= float(self.I[i][1]) for i in self.I), name="R3")
        
        # Función objetivo
        objetivo = quicksum(float(self.J[j]) * x_j[j] for j in self.J.keys())
        model.setObjective(objetivo, GRB.MINIMIZE,)
        
        # Optimizamos el problema
        model.optimize()
        return model, x_j
        
    def manejo_soluciones(self, model, x_j):
        
        # Manejo de soluciones
        print("\n"+"-"*10+" Manejo Soluciones "+"-"*10)
        print(f"El valor objetivo es de: {model.ObjVal}", "{peso/kg}")
        print()
        print("Variables de decision:")
        
        for j in self.J:
            print(f"Se debe utilizar {x_j[j].x} kilogramos de {j}")
        print("\n"+"-"*9+" Restricciones Activas "+"-"*9)
        
        for constr in model.getConstrs():
            if constr.getAttr("slack") == 0:
                print(f"La restriccion {constr} está activa")

if __name__ == '__main__':
    modelo = Modelo()
    modelo.manejo_soluciones(*modelo.implementar_modelo())
    
    
