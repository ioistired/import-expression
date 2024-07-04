import ast
import codecs, io, encodings
from encodings import utf_8

try:
	from ast import unparse
except ImportError:
	# py < 3.9
	from astunparse import unparse

import import_expression as ie

def encode(input: str, errors="strict"):
	raise NotImplementedError

def decode(b, errors='strict'):
	if not b:
		return '', 0

	decoded = codecs.decode(b, errors=errors, encoding='utf-8')
	parsed = ie.parse(decoded)
	unparsed = unparse(parsed)
	return unparsed, len(decoded)

class IeDecoder(codecs.BufferedIncrementalDecoder):
	'''"incremental decoder" in name only, for it is neither'''
	def decode(self, b, final=False):
        self.buffer += b
        if final:
            buffer = self.buffer
            super().reset()
            return decode(buffer)[0]
        return ""

def search_function(encoding, codec_names={'import_expression', 'ie'}):
	if encoding not in codec_names:  # pragma: no cover
		return None
	return codecs.CodecInfo(
		name='import_expression',
		encode=encode,
		decode=decode,
		incrementalencoder=utf_8.IncrementalEncoder,
		incrementaldecoder=IeDecoder,
		streamreader=utf_8.StreamReader,
		streamwriter=utf_8.StreamWriter,
	)

def register():
	codecs.register(search_function)
