from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from sqlalchemy import Column, Integer, DateTime
from flask_cors import CORS
from bs4 import BeautifulSoup
from urllib.request import urlopen
from io import BytesIO
from IPython import display

import json 
import os
import datetime
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import base64
import matplotlib.dates as matdates

app = Flask(__name__)
cors = CORS(app)

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'crud.sqlite')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = 'False'

db = SQLAlchemy(app)
ma = Marshmallow(app)

nomes = ['Timestamp', 'Consumo Total', 'Consumo Iluminacao', 'Consumo Servidor', \
			'Consumo Rede', 'Consumo Bancadas', 'Consumo Ar Condicionado']

df_labsoft = pd.read_csv(r"medicoes_labsoft.csv", names=nomes)

df_labsoft['Timestamp'] = pd.to_datetime(df_labsoft['Timestamp'])

################################################## M O D E L S ##################################################
class Aparelho(db.Model):
	__tablename__ = 'aparelho'
	id = db.Column(db.Integer, primary_key=True)
	status = db.Column(db.String(50), unique=False)
	marca = db.Column(db.String(50), unique=False)
	modelo = db.Column(db.String(50), unique=False)
	local = db.Column(db.String(50), unique=False)
	nome = db.Column(db.String(50), unique=True)

	def __init__(self, local, nome, marca = "Nenhum", modelo = "Nenhum", status = "Desligado"):
		self.status = status
		self.marca = marca
		self.modelo = modelo
		self.local = local
		self.nome = nome

################################################## S C H E M A ##################################################
class AparelhoSchema(ma.Schema):
    class Meta:
        # Fields to expose
        fields = ('id', 'status', 'marca', 'modelo', 'local', 'nome')

aparelho_schema = AparelhoSchema()
aparelhos_schema = AparelhoSchema(many=True)

################################################## R O U T E S ##################################################
@app.route("/")
def homepage():
	text = "Este eh o backend da aplicacao ThermoSmart. Voce pode acessar os endpoints aqui descritos."

	response = {
		"status_code": 200,
		"message": text,
		"/info [GET]": "retorna um json com as informacoes de gasto de energia ",
		"/info/aparelho [POST]": "cria um novo aparelho no banco de dados",
		"/info/aparelho/id [PUT]": "altera o status do aparelho de acordo com o seu id"
	} 
	return jsonify(response)

# endpoint to show all lines
@app.route("/info", methods=['GET'])
def get_info():

	response = {}

	response['aparelhos'] = {}

	response['previsao'] = {
		'cidade': 'Sao Paulo',
		'grafico': plot_previsao('244')
	}

	if request.method == 'GET':
		all_aparelhos = Aparelho.query.all()

		if len(all_aparelhos) > 0: 
			for aparelho in all_aparelhos:
				id = str(aparelho.id)

				response['aparelhos'][id] = {
					'aparelho': aparelho.nome,
					'local': aparelho.local,
					'marca': aparelho.marca,
					'modelo': aparelho.modelo,
					'status': aparelho.status,
					'grafico': plot_encoded(df_labsoft,"Consumo "+aparelho.nome.title()),
				}

		return jsonify(response)

	return jsonify(response)

	
# endpoint to show all lines
@app.route("/info/aparelho", methods=['POST'])
def create_aparelho():
	response = {}
	if request.method == 'POST':
		status = request.json['status']
		marca = request.json['marca']
		modelo = request.json['modelo']
		local = request.json['local']
		nome = request.json['nome']

		novo_aparelho = Aparelho(status, marca, modelo, local, nome)
		db.session.add(novo_aparelho)
		db.session.commit()

		response = aparelho_schema.dump(novo_aparelho)
		print("\n \n \n \n")
		print(response,type(response))
		print("\n \n \n \n")

		return jsonify(response)

	return jsonify("Aparelho nao foi adicionado.")

# endpoint to update line
@app.route("/info/aparelho/<id>", methods=["PUT"])
def update_aparelho(id):
	if request.method == 'PUT':
		aparelho = Aparelho.query.get(id)

		if aparelho is not None:
			if aparelho.status == "Desligado":
				aparelho.status = "Ligado"
			else:
				aparelho.status = "Desligado"	
			
			db.session.commit()

			return aparelho_schema.jsonify(aparelho) 
		pass
	return jsonify("Aparelho nao encontrado.")

############################################################################################################

def plot_encoded(df,nome):
	ax = plt.gca()
	ax.set_facecolor('#333333')
	ax.tick_params(labelcolor='white')

	df.plot(kind='line',x='Timestamp',y=nome,ax=ax)

	majorFmt = matdates.DateFormatter('%Y-%m-%d, %H:%M:%S')  

	ax.xaxis.set_major_formatter(majorFmt)
	plt.setp(ax.xaxis.get_majorticklabels(), rotation=80)
	plt.tight_layout()

	fig1 = plt.gcf()
	tmpfile = BytesIO()
	fig1.savefig(tmpfile, format='png', transparent=True)

	plt.clf()
	fig1.clf()

	return base64.b64encode(tmpfile.getvalue()).decode('utf-8')

def plot_previsao(codigo="244"):
	dict_previsao = previsao(codigo)

	df_previsao = pd.DataFrame.from_dict(dict_previsao, orient='index', columns=['Dia', 'Máxima Temperatura', 'Mínima Temperatura'])
	df_previsao['Dia'] = pd.to_datetime(df_previsao['Dia'])
	# gca stands for 'get current axis'
	ax = plt.gca()
	ax.set_facecolor('#333333')
	ax.tick_params(labelcolor='white')
	df_previsao.plot(kind='line',x='Dia',y='Máxima Temperatura',ax=ax, color='tomato')
	df_previsao.plot(kind='line',x='Dia',y='Mínima Temperatura',ax=ax)

	plt.setp(ax.xaxis.get_majorticklabels(), rotation=80)
	plt.tight_layout()

	fig1 = plt.gcf()
	tmpfile = BytesIO()
	fig1.savefig(tmpfile, format='png', transparent=True)

	plt.clf()
	fig1.clf()

	return base64.b64encode(tmpfile.getvalue()).decode('utf-8')

def previsao(codigo):
	previsoes = {}

	html = urlopen("http://servicos.cptec.inpe.br/XML/cidade/"+codigo+"/previsao.xml").read()
	soup = BeautifulSoup(html, 'html.parser')

	for dado in soup.find_all('cidade'):
		i = 0
		for previsao in dado.find_all('previsao'):
			previsoes[i] = []
			previsoes[i].append(previsao.find('dia').get_text())
			previsoes[i].append(float(previsao.find('maxima').get_text()))
			previsoes[i].append(float(previsao.find('minima').get_text()))
			i+=1

	return previsoes

if __name__ == '__main__':
    app.run(debug=True)
