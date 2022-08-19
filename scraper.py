import bs4.element
from bs4 import BeautifulSoup
from dataclasses import dataclass
import requests
import json
import re
from threading import Lock, Thread
import sys
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
	extras: list
	context: set
	sinonimos: list


@dataclass
class Resultado:
	header: list  # Match, pode apenas ser uma str, vamos ver
	definicoes: list  # Definicao
	palavra: str  # A match no dicionário


link = "https://dicionario.priberam.org/"
i = 1


def getHeader(soup):
	defHeader = soup.find('div', class_='defheader')
	defHeaderDivs1 = defHeader.find_all('div')

	defHeaderDiv2 = []

	for (j, d) in enumerate(defHeaderDivs1):
		if defHeaderDivs1[j].text != '':
			defHeaderDiv2 = list(defHeaderDivs1[j].children)
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
	# Navegação pela árvore dos resultados, no final isto tem-se a lista com os divs correspondentes às definições das
	# palavras
	resultados = list(soup.find('div', id='resultados').div.children)
	resultados = [r for r in resultados if r != '\n']
	resultados = list(resultados[-1].children)
	resultados = [r for r in resultados if not isinstance(r, bs4.element.NavigableString) and r.find('div')]

	output = []

	for resultado in resultados:

		# Para cada resultado, são tratadas as palavras caso sejam estrangeirismos
		verbeteh = resultado.find('span', class_='verbeteh1')
		if verbeteh is not None:
			palavraPT = verbeteh.find('h2').find('span', class_='varpt')
			if palavraPT is not None:
				palavra = ''.join(palavraPT.text.split())
			else:
				palavra = verbeteh.find('h2').text

			palavra = re.sub(r'\|.*\|', '', palavra)

		else:
			break

		# Quem tiver solução melhor está convidado a educar-me, eu sou mau.
		origem = ""
		childreen = resultado.find('span', class_='verbeteh1').parent.children
		childreen = [c.text for c in childreen]

		for k, c in enumerate(childreen):
			if c == '(':
				for j in range(k, len(childreen)):
					origem += childreen[j]
					if childreen[j] == ')':
						break

			# Se a origem já foi encontrada, rua
			elif origem != '':
				break

		classe = resultado.find('categoria_ext_aao').text

		defsRaw = resultado.find_all('p')
		for d in defsRaw:

			if d.find('dominio_ext_pb') is not None:
				trash = d.find('dominio_ext_pb')
				trash.decompose()

			if d.find('span', class_="varpb") is not None:
				trash = d.find('span', class_="varpb")
				trash.decompose()

		defs, extras, sinonimos = [], [], []

		for d in defsRaw:
			novo = re.sub(' {2,}|\\n|\\xa0|\[\]', '', d.text)
			if "Sinónimo Geral:" in novo:
				sinonimos.extend(re.sub("Sinónimo Geral:", '', novo).split())
			elif '•' in novo:
				extras.append(novo)
			else:
				defs.append(novo)

		context = set()
		for d in defs:
			s = re.search('\[[^\]]*\]', d)
			if s is not None:

				s = re.sub('[\[\]]', '', s.group())
				lista = s.split(', ')
				for elem in lista:
					context.add(elem)

		newDef = Definicao(palavra, origem, classe, defs, extras, context, sinonimos)
		output.append(newDef)

	return output


def bold(string):
	return "\033[1m" + string + "\033[0m"


def underline(string):
	return "\033[4m" + string + "\033[0m"


def red(string):
	return '\033[0;31m' + string + "\033[0m"


def green(string):
	return '\033[0;32m' + string + "\033[0m"


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


def checkWord(soup, pal, err, wLock):
	error = ""
	check = soup.find('div', id='resultados')
	if "Palavra não encontrada" in check.text:
		error += "Error: "

	check = soup.find('div', class_='alert alert-info')
	if check is not None:
		errorMessage = ""

		if 'Sugerir' in check.text:
			errorMessage += f'Palavra ({pal}) não encontrada. Sem sugestões'
		else:
			errorMessage += f'Palavra ({pal}) não encontrada. Sugestões:'

		error += errorMessage
		sugestoes = soup.find('div', class_='pb-sugestoes-afastadas').text.replace('\n', ' | ')
		error += sugestoes
		wLock.acquire()
		err.write(error.replace('\n', ' ') + '\n')
		wLock.release()

	return error


def makeRequest(pal, f, err, wLock):
	request = link + pal
	htmlResponse = requests.get(request)

	if htmlResponse.status_code != 200:
		print(f"Failed na palavra {pal}, request inválido. Code {htmlResponse.status_code}")

	else:
		htmlText = htmlResponse.text
		soup = BeautifulSoup(htmlText, 'lxml')

		error = checkWord(soup, pal, err, wLock)
		if error != "":
			print(bold(pal) + '\n')
			print(error)

		else:

			header = getHeader(soup)
			defs = getDefs(soup)
			resultado = Resultado(header, defs, pal)

			dic = {
				resultado.palavra: {

					"palavra": None if resultado.palavra == "" else resultado.palavra,
					# Este header ainda ta meio ranhoso
					"header": None if resultado.header == [] else [[e.palavra, e.tipo] for e in resultado.header],
					"def": None if resultado.definicoes == [] else [{
						"palavra": None if e.palavra == "" else e.palavra,
						"origem": None if e.origem == "" else e.origem,
						"tipo": None if e.tipo == "" else e.tipo,
						"defs": None if e.defs == [] or e.defs == [""] else e.defs,
						"extras": None if e.extras == [] else e.extras,
						"contexto": None if list(e.context) == [] else list(e.context),
						"sinónimos": None if e.sinonimos == [] else e.sinonimos
					} for e in resultado.definicoes]
				}
			}

			jsonStr = json.dumps(dic, ensure_ascii=False, indent=4)
			wLock.acquire()
			global i
			print(str(i) + " " + pal)
			if i != 1:
				f.write(',')
			i += 1
			f.write(jsonStr[1:-1])
			wLock.release()
			dic.clear()


# 999 282 palavras
def main():
	args = sys.argv[1:]

	if len(args) > 1:
		mode = 'a'
		trueCount = int(args[1]) - 1
	else:
		mode = 'w'
		trueCount = 0

	f = open(args[0], mode, encoding='utf-8')

	if mode == 'w':
		f.write('{\n')
	else:
		f.write(',')

	r = open("dics/teste.txt", 'r', encoding="ISO-8859-1")
	err = open("err.log", mode, encoding="ISO-8859-1")

	rLock = Lock()
	wLock = Lock()
	threads = []

	lines = r.readlines()[trueCount:]

	for line in lines:

		if line == "":
			break

		rLock.acquire()
		pal = line[:-1]
		rLock.release()

		# Sequencial
		# makeRequest(pal, f, err, wLock)

		# Concorrente
		t = Thread(target=makeRequest, args=(pal, f, err, wLock))
		threads.append(t)
		time.sleep(0.15)
		t.start()

	for t in threads:
		t.join()

	f.write('}\n')
	f.close()
	err.close()
	r.close()


if __name__ == "__main__":
	main()
