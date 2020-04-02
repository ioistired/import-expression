try:
	from .codec import register
except ImportError:
	pass
else:
	register()
