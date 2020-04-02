import ast
from . import codec_compat as astunparse
import codecs, io, encodings
from encodings import utf_8

import import_expression as ie
from import_expression.constants import IMPORTER

IMPORT_STATEMENT = ast.parse(f'from importlib import import_module as {IMPORTER}').body[0]

def decode(b, errors='strict'):
	s, length = utf_8.decode(b, errors)
	parsed = ie.parse(s)
	parsed.body.insert(0, IMPORT_STATEMENT)
	unparsed = astunparse.unparse(parsed)
	return unparsed, len(unparsed)

def ie_transform(stream):
	return decode(stream.read())

class ImportExpressionIncrementalDecoder(utf_8.IncrementalDecoder):
	def decode(self, input, final=False):
		self.buffer += input
		if final:
			buf = self.buffer
			self.buffer = b''
			return super().decode(decode(buf).encode('utf-8'), final=True)
		return ''

class ImportExpressionStreamReader(utf_8.StreamReader):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.stream = io.StringIO(ie_transform(self.stream))

def search_function(encoding):
	if encoding != 'import_expression':
		return None
	utf8 = encodings.search_function('utf8')
	return codecs.CodecInfo(
		name='import_expression',
		encode=utf8.encode,
		decode=decode,
		incrementalencoder=utf8.incrementalencoder,
		incrementaldecoder=ImportExpressionIncrementalDecoder,
		streamreader=ImportExpressionStreamReader,
		streamwriter=utf8.streamwriter,
	)

def register():
	codecs.register(search_function)
