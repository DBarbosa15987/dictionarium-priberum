from bs4 import BeautifulSoup
from dataclasses import dataclass
import requests
import sys
import json
import re


@dataclass
class Resultado:
	header: list  # Match, pode apenas ser uma str, vamos ver
	definicoes: list  # Definicao


@dataclass
class Match:
	palavra: str
	tipos: list  # Pode ser ignorado


@dataclass
class Definicao:
	palavra: str
	origem: str
	tipo: str
	defs: list
	context: set


link = "https://dicionario.priberam.org/"


def getHeader(soup):
	defHeader = soup.find('div', class_='defheader')
	defHeaderDivs = defHeader.find('div').find_all('div')
	matches = []

	for match in defHeaderDivs:
		word = match.find('span', class_='varpt').text
		classesList = match.find_all('em')
		classes = [classe.text for classe in classesList]
		matches.append(Match(word, classes))

	return matches


def getDefs(soup):
	# Navegação pela árvore dos resultados, no final isto tem-se a lista com os divs correspondentes às definições das palavras
	resultados = list(soup.find('div', id='resultados').div.children)
	resultados = [r for r in resultados if r != '\n']
	resultados = list(resultados[-1].children)
	resultados = [r for r in resultados if r != '\n' and r.find('div')]

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
		defs = [re.sub(' {2,}|\\n|\\xa0|\[\]', '', d) for d in defs] # ' {2,}|\\n|\\xa0|\[\]'

		context = set()
		for d in defs:
			s = re.search('\[[^\]]*\]', d) # \[[^\]]*\]
			if s is not None:

				s = re.sub('[\[\]]', '', s.group())
				lista = s.split(', ')
				for elem in lista:
					context.add(elem)

		newDef = Definicao(palavra, origem, classe, defs, context)
		print(newDef, end='\n\n')


def main():
	args = sys.argv[1:]
	pal = args[0]
	# with open(args[1], 'w') as f:
	# 	print(f"{args[1]} criada\n")

	request = link + pal
	htmlResponse = requests.get(request)
	htmlText = htmlResponse.text
	soup = BeautifulSoup(htmlText, 'lxml')

	matches = getHeader(soup)
	# print(matches, end='\n')

	getDefs(soup)


if __name__ == "__main__":
	main()
