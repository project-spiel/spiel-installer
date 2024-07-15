pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'spielinstaller'
gnome = import('gnome')

gnome.compile_resources('spielinstaller',
  'spielinstaller.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python_module = import('python')
python = python_module.find_installation(
  'python3', modules: ['langcodes', 'language_data'])

conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)
conf.set('prefix', get_option('prefix'))

configure_file(
  input: 'spiel-installer.in',
  output: 'spiel-installer',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'r-xr-xr-x'
)

spielinstaller_sources = [
  '__init__.py',
  'main.py',
  'voices_store.py',
  'voice_row.py',
  'window.py',
]

install_data(spielinstaller_sources, install_dir: moduledir)
