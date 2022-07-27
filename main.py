import bs4.element
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
	defHeaderDivs1 = defHeader.find_all('div')

	defHeaderDiv2 = []

	for (i, d) in enumerate(defHeaderDivs1):  # ver o 'nado'
		if defHeaderDivs1[i].text != '':
			defHeaderDiv2 = list(defHeaderDivs1[i].children)
			defHeaderDiv2 = [e for e in defHeaderDiv2 if not isinstance(e, bs4.element.NavigableString)]
			break
		else:
			pass

	matches = []

	# tratar aqui dos acordos ortográficos
	for match in defHeaderDiv2:
		maybeWord = match.find('span', class_='varpt')
		if len(list(maybeWord.children)) > 0:
			pass
			word = maybeWord.find('span', class_='varpt')
			if word is None:
				word = maybeWord.text
			else:
				word = word.text
		else:
			word = maybeWord.text

		classe = match.find('em')
		if classe is None:
			classe = match.contents[0].strip() + ' ' + match.find('a').find('span', class_='varpt').text
		else:
			classe = classe.text

		matches.append(Header(word, classe))

	return matches


def getDefs(soup):
	# Navegação pela árvore dos resultados, no final isto tem-se a lista com os divs correspondentes às definições das palavras
	resultados = list(soup.find('div', id='resultados').div.children)
	resultados = [r for r in resultados if r != '\n']
	resultados = list(resultados[-1].children)
	resultados = [r for r in resultados if not isinstance(r, bs4.element.NavigableString) and r.find('div')]

	output = []

	for resultado in resultados:

		# 'metro- metro- 1' -> 'metro- 1'

		# Isto aqui refere-se a uma definição, se o valor for None podem ser palavras relacionadas e tal...
		palavraList = resultado.find('span', class_='verbeteh1')
		if palavraList is not None:
			palavraList = palavraList.find('h2').text.split()[1:]
			palavra = ''.join(palavraList)
		else:
			break

		# Quem tiver solução melhor está convidado a educar-me, eu sou mau.
		origem = ""
		childreen = resultado.find('span', class_='verbeteh1').parent.children
		childreen = [c.text for c in childreen]

		for i, c in enumerate(childreen):
			if c == '(':
				for j in range(i, len(childreen)):
					origem += childreen[j]
					if childreen[j] == ')':
						break

			# Se a origem já foi encontrada, rua
			elif origem != '':
				break

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
		for deff in def_.defs:
			print(deff)
		print('\n')


def checkWord(soup, pal, err):
	error = ""
	check = soup.find('div', id='resultados')
	if "Palavra não encontrada" in check.text:
		error += "Error: "

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
		err.write(error.replace('\n', ' ') + '\n')
		sugestoes = soup.find('div', class_='pb-sugestoes-afastadas').text
		error += sugestoes

	return error


# !! O METRÔ AINDA APARECE E SINÓNIMOSINÔNIMO
# 40.[Portugal: Alentejo][Portugal: Alentejo][Música]Solista que inicia uma moda no cante alentejano.",
# "palavra": "|ô|tor·re|ô|",
# 999282 palavras
def main():
	f = open("test.json", 'w', encoding='utf-8')
	f.write('{\n')
	r = open("dics/wordlist-big-latest.txt", 'r', encoding="ISO-8859-1")
	err = open("err.log", 'w', encoding='utf-8')
	i = 1

	while True:

		pal = r.readline()

		if pal == "":
			break
		print(str(i) + " " + pal)

		# remover o '\n' do readline()
		pal = pal[:-1]
		request = link + pal
		htmlResponse = requests.get(request)

		if htmlResponse.status_code != 200:
			print(f"Failed na palavra {pal}, request inválido. Code {htmlResponse.status_code}")

		else:
			htmlText = htmlResponse.text
			soup = BeautifulSoup(htmlText, 'lxml')

			error = checkWord(soup, pal, err)
			if error != "":
				print(bold(pal) + '\n')
				print(error)

			else:

				if i != 1:
					f.write(',\n')
				i += 1

				header = getHeader(soup)
				defs = getDefs(soup)
				resultado = Resultado(header, defs, pal)

				dic = {resultado.palavra: {

					"palavra": resultado.palavra,
					# Este header ainda ta meio ranhoso
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

				jsonStr = json.dumps(dic, ensure_ascii=False, indent=4)
				f.write(jsonStr[1:-1])
				dic.clear()

	f.write('}\n')
	f.close()
	err.close()
	r.close()


if __name__ == "__main__":
	main()
