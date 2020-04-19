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

nomes = ['Timestamp', 'Consumo Total', 'Consumo Iluminacao', 'Consumo Servidor', \
			'Consumo Rede', 'Consumo Ar Condicionado', 'Consumo Bancadas']

df_labsoft = pd.read_csv(r"medicoes_labsoft.csv", names=nomes)

df_labsoft['Timestamp'] = pd.to_datetime(df_labsoft['Timestamp'])

################################################## R O U T E S ##################################################
@app.route("/")
def homepage():
	text = "Este eh o backend da aplicacao ThermoSmart. Voce pode acessar os endpoints aqui descritos."

	response = {
		"status_code": 200,
		"message": text,
		"/info [GET]": "retorna um json com as informações de gasto de energia ",
		"/info/<id>/status [POST]": "altera o status do aparelho de acordo com o seu id"
	} 
	return jsonify(response)

# endpoint to show all lines
@app.route("/info", methods=['GET'])
def get_info():

	response = {}

	if request.method == 'GET':
		response = {
			'aparelhos': {
				'1': {
					'aparelho': 'Iluminacao',
					'grafico': plot_encoded(df_labsoft,"Consumo Iluminacao"),
					'status': ''
				},
				'2': {
					'aparelho': 'Ar Condicionado',
					'grafico': plot_encoded(df_labsoft,"Consumo Ar Condicionado"),
					'status': ''
				},
				'3': {
					'aparelho': 'Rede',
					'grafico': plot_encoded(df_labsoft,"Consumo Rede"),
					'status': ''
				},
			},
			'previsao': {
				'cidade': 'Sao Paulo',
				'grafico': plot_previsao('244')
			}
		}

		return jsonify(response)

	return jsonify(response)

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
	fig1.savefig(tmpfile, format='png')

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
	fig1.savefig(tmpfile, format='png')

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
