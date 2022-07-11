from bs4 import BeautifulSoup
from dataclasses import dataclass
import requests
import sys
import json
import re

@dataclass
class Header:
	palavra: str
	tipo: str  # Pode ser ignorado


@dataclass
class Definicao:
	palavra: str
	origem: str
	tipo: str
	defs: list
	context: set


@dataclass
class Resultado:
	header: list  # Match, pode apenas ser uma str, vamos ver
	definicoes: list  # Definicao
	palavra: str


link = "https://dicionario.priberam.org/"


def getHeader(soup):
	defHeader = soup.find('div', class_='defheader')
	defHeaderDivs = defHeader.find('div').find_all('div')
	matches = []

	for match in defHeaderDivs:
		word = match.find('span', class_='varpt').text
		classes = match.find('em').text
		matches.append(Header(word, classes))

	return matches


def getDefs(soup):
	# Navegação pela árvore dos resultados, no final isto tem-se a lista com os divs correspondentes às definições das palavras
	resultados = list(soup.find('div', id='resultados').div.children)
	resultados = [r for r in resultados if r != '\n']
	resultados = list(resultados[-1].children)
	resultados = [r for r in resultados if r != '\n' and r.find('div')]

	output = []

	for resultado in resultados:

		# 'metro- metro- 1' -> 'metro- 1'
		palavraList = resultado.find('span', class_='verbeteh1').text.split()[1:]
		palavra = ''.join(palavraList)

		origem = resultado.find('span', class_='def').text

		classe = resultado.find('categoria_ext_aao').text

		defs = resultado.find_all('p')
		for d in defs:

			if d.find('dominio_ext_pb') is not None:
				trash = d.find('dominio_ext_pb')
				trash.decompose()

		defs = [d.text for d in defs]
		defs = [re.sub(' {2,}|\\n|\\xa0|\[\]', '', d) for d in defs]

		context = set()
		for d in defs:
			s = re.search('\[[^\]]*\]', d)
			if s is not None:

				s = re.sub('[\[\]]', '', s.group())
				lista = s.split(', ')
				for elem in lista:
					context.add(elem)

		newDef = Definicao(palavra, origem, classe, defs, context)
		output.append(newDef)

	return output


def bold(str):
	return "\033[1m" + str + "\033[0m"


def underline(str):
	return "\033[4m" + str + "\033[0m"


def pp(resultado):

	print(bold(resultado.palavra) + '\n')
	for h in resultado.header:
		print(bold(h.palavra) + ': ' + h.tipo)
	print('\n')

	for def_ in resultado.definicoes:
		print(bold(def_.palavra) + ", " + def_.tipo)
		print('(' + def_.origem + ')\n')
		for deff in def_.defs:
			print(deff)
		print('\n')


def main():
	args = sys.argv[1:]
	pal = args[0]
	# f = open(args[1], 'w')

	request = link + pal
	htmlResponse = requests.get(request)
	htmlText = htmlResponse.text
	soup = BeautifulSoup(htmlText, 'lxml')

	header = getHeader(soup)
	defs = getDefs(soup)

	resultado = Resultado(header, defs, pal)
	pp(resultado)


if __name__ == "__main__":
	main()
