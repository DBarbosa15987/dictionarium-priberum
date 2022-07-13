from bs4 import BeautifulSoup
from dataclasses import dataclass
import requests
import sys
import json
import re
import time


@dataclass
class Header:
	palavra: str  # A variação da palavra
	tipo: str  # Pode ser ignorado


@dataclass
class Definicao:
	palavra: str  # A variação da palavra
	origem: str
	tipo: str
	defs: list
	context: set


@dataclass
class Resultado:
	header: list  # Match, pode apenas ser uma str, vamos ver
	definicoes: list  # Definicao
	palavra: str  # A match no dicionário


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


def bold(string):
	return "\033[1m" + string + "\033[0m"


def underline(string):
	return "\033[4m" + string + "\033[0m"


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


def checkWord(soup, pal):
	error = ""
	check = soup.find('div', class_='alert alert-info')

	if check is not None:
		errorMessage = ""

		if 'Sugerir' in check.text:
			errorMessage += f'Palavra ({pal}) não encontrada. Pode sugerir a adição da palavra no site do dicionário priberam, '
			errorMessage += 'eu aqui só faço scrape.'
		else:
			errorMessage += f'Palavra ({pal}) não encontrada. Será que procura alguma destas palavras abaixo?\n'
			errorMessage += 'Se não, sei lá.\n'

		error += errorMessage
		sugestoes = soup.find('div', class_='pb-sugestoes-afastadas').text
		error += sugestoes

	return error


# !! O METRÔ AINDA APARECE E SINÓNIMOSINÔNIMO
# CONJUGARCONJUGAR
# 999282 palavras
def main():
	# args = sys.argv[1:]
	# pal = args[0]
	f = open("test.json", 'a', encoding='utf-8')
	f.write('{\n')
	r = open("dics/z.txt", 'r', encoding="ISO-8859-1")
	i = 1

	while True:

		pal = r.readline()

		print(str(i) + " " + pal)

		# Sim, parece que o python é lazy
		# acabou or \n or coisas de teste
		if pal == "" or pal[0] == '\n' or pal[0] != 'z':
			break

		# remover o '\n' do readline()
		pal = pal[:-1]
		request = link + pal
		htmlResponse = requests.get(request)
		# time.sleep(2)

		if htmlResponse.status_code != 200:
			print(f"Failed na palavra {pal}, request inválido. Code {htmlResponse.status_code}")
		# return

		else:
			htmlText = htmlResponse.text  # .encode('latin1', 'ignore').decode('utf8', 'ignore')
			soup = BeautifulSoup(htmlText, 'lxml')

			error = checkWord(soup, pal)
			if error != "":
				print(bold(pal) + '\n')
				print(error)
				pass

			else:

				if i != 1:
					f.write(',\n')
				i += 1

				header = getHeader(soup)
				defs = getDefs(soup)
				resultado = Resultado(header, defs, pal)

				# dic = {resultado.palavra: [
				# 	resultado.palavra,
				# 	[[e.palavra, e.tipo] for e in resultado.header],
				# 	[[e.palavra, e.origem, e.tipo, e.defs, list(e.context)] for e in resultado.definicoes]
				# ]}

				dic = {resultado.palavra: {

					"palavra": resultado.palavra,
					"header": [[e.palavra, e.tipo] for e in resultado.header],
					"def": [{
						"palavra": e.palavra,
						"origem": e.origem,
						"tipo": e.tipo,
						"defs": e.defs,
						"contexto": list(e.context)
					} for e in resultado.definicoes]
				}

				}

				# print(dic)
				jsonStr = json.dumps(dic, ensure_ascii=False, indent=4)
				f.write(jsonStr[1:-1])
				dic.clear()

	f.write('}\n')
	f.close()


# pp(resultado)


if __name__ == "__main__":
	main()
