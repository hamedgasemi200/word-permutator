import argparse
import click
import csv
import re

from datetime import datetime
from peewee import *


def REGEXP(expr, item):
    reg = re.compile(expr, re.I)
    return reg.search(item) is not None

class Generator():

    def __init__(self, model:object) -> None:
        # Set version
        self.version = '2.5.2'
        self.model = model

        # Configure connection
        self.model.create_table(True)
        self.model._meta.database.register_function(REGEXP, 'REGEXP', num_params=2)
    
    def fromcsv(self, filename:str) -> None:
        with open(filename, newline='') as csvfile:
            insertions = 0
            reader = csv.DictReader(csvfile, skipinitialspace=True, quotechar='"', delimiter=',')
            for i, row in enumerate(list(reader)):
                if not self.model.select().where(self.model.word == row['word']).exists():
                    del row['id']
                    self.model.insert(row).execute()
                    insertions += 1
                    print(" {}. ✓ Inserted '{}'.".format(i+1, row['word']))
            
            if not insertions: print('\n\t > There is nothing new to import.\n')
        
    def export(self, filename:str) -> None:
        print("\n\tStart exporting rows to '{}'.\n".format(filename))

        words = self.model.select().tuples()

        with open(filename, 'w') as csvfile:
            csvfile.write(','.join(self.model._meta.columns.keys()) + '\n')
            for i, values in enumerate(words):
                csvfile.write(','.join(map(str, ['"{}"'.format(value) for value in values])) + '\n')
        csvfile.close()
        
        print("\t ✓ Exported {} words successfully.\n".format(words.count()))

    def insert(self, words:list, language:str) -> None:
        insertions = 0

        # Start message
        print('\n\t > Start inserting.\n')

        # Iterate through words
        for i, word in enumerate([w.strip() for w in words]):
            if self.model.select().where(self.model.word == word).exists():
                print("\t {}. Word '{}' already exists.".format(i, word))
            else:
                # Insert word to words list
                self.model.insert(word=word, length=len(word), language=language).execute()
                
                # Increase insertions
                insertions += 1
                
                # Show insertion message
                print("\t {}. ✓ Inserted '{}'.".format(i, word))
        
        # Finish message
        print('\n\t > Inserted {} words.\n'.format(insertions))
    
    def delete(self, words:list) -> None:
        if click.confirm('\n\t i) Do you want to continue?\n', default=True):
            print('')
            # Iterate through words
            for i, word in enumerate(words):
                if self.model.select().where(self.model.word == word).exists():
                    # Delete row
                    self.model.get(self.model.word == word).delete_instance()

                    # Show message
                    print("\t {}. ✓ deleted '{}'.".format(i, word))
                else:
                    print("\t {}. ✕ Word '{}', not found.".format(i, word))
            
            # Finish message
            print('\n\t Finished deleting words\n')
        else:
            print('\n\t ⏹ Canceled deleting.\n')
    
    def words(self, args:dict) -> None:
        words = self.model.select()
        
        if args.values: words = words.where(self.model.word.regexp("^[{}]+$".format( "".join( set(args.values[0].strip()) ))))
        if args.language: words = words.where(self.model.language == args.language)
        if args.lessthan: words = words.where(self.model.length <= args.lessthan)
        if args.morethan: words = words.where(self.model.length >= args.morethan)
        words = words.order_by(self.model.length[args.order]()) if args.order else words.order_by(self.model.word.desc())

        # Message
        print("\n\t ✍️  Showing words with.\n")
        
        # Show every single word
        for i, word in enumerate(words):
            print(' {})'.format(i+1), word.word)
    
    def find(self, word:str) -> None:
        if self.model.select().where(self.model.word == word).exists():
            print("\n\t ✅ '{}' is found.\n".format(word))
        else:
            print("\n\t 🚫 '{}' not found.\n".format(word))

if __name__ == "__main__":
    # Get methods list
    methods = [func for func in dir(Generator) if callable(getattr(Generator, func)) and not func.startswith('__')]

    # Set argument parser
    parser = argparse.ArgumentParser(prog='WordCatcher', description='get possible words with give letters and length.')

    # Set parameters
    parser.add_argument('command', type=str, choices=methods)
    parser.add_argument('values', type=str, nargs='*', help='set a list of value for the given command.')
    parser.add_argument('-db', '--database', type=str, default='words.db', help='set database name (default: words.db)')
    parser.add_argument('-t', '--table', type=str, default='words', help='set words table name (default: words)')
    parser.add_argument('-o', '--order', type=str, choices=['asc', 'desc'], help='define order type (default: asc).')
    parser.add_argument('-la', '--language', type=str, default='fa', help='define the language of the word (default: fa).')
    parser.add_argument('-lt', '--lessthan', type=int, help='length of the words must be less than/euqal to the given value.')
    parser.add_argument('-mt', '--morethan', type=int, help='length of the words must be more than/equal to the given value.')
    args = parser.parse_args()
    
    # Define model
    class WordModel(Model):
        class Meta:
            database = SqliteDatabase(args.database)
            db_table = args.table
        
        id = AutoField()
        word = CharField(null=False, unique=True)
        language = CharField(null=True)
        length = IntegerField(null=False)
    
    # Make generator
    generator = Generator(WordModel)

    # Run methods
    if args.command == 'insert': generator.insert(args.values, args.language) if args.values else print(' > Words must be defined.')
    elif args.command == 'delete': generator.delete(args.values) if args.values else print(' > Words must be defined.')
    elif args.command == 'find': generator.find(args.values[0].strip()) if args.values else print(' > Word must be defined.')
    elif args.command == 'export': generator.export( args.values[0].strip() if args.values else 'export-{}.csv'.format(datetime.now().strftime('%Y-%m-%d %X')) )
    elif args.command == 'fromcsv': generator.fromcsv(args.values[0].strip()) if args.values else print(' > CSV file name must be defined.')
    elif args.command == 'words': generator.words(args)
    else: print('Action is not defined.')