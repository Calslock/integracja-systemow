import argparse, csv
import prettytable as pt

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=open, default="katalog.txt")
args = parser.parse_args()

csvreader = csv.reader(args.file, delimiter=";")
names = ['Lp.', 'Producent', 'Przekątna', 'Rozdzielczość', 'Typ ekranu', 'Dotykowy ekran', 'CPU', 'Rdzenie', 'Taktowanie [MHz]', 'Ilość RAM', 'Pojemność dysku', 'Rodzaj dysku', 'GPU', 'Pamięć GPU', 'OS', 'Napęd ODD']
producers = []
t = pt.PrettyTable(names)

for number, item in enumerate(csvreader):
    producers.append(item[0])
    item.insert(0, number+1)
    item.pop()
    t.add_row(item)

print(t)
print(dict(sorted((x, producers.count(x)) for x in set(producers))))
