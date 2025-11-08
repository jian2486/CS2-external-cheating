# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('CS2-external-cheating', 'CS2-external-cheating')],
    hiddenimports=['pynput', 'pynput.keyboard', 'pynput.mouse'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

# 添加图标和字体资源
a.datas += Tree('./src/img', prefix='src/img', excludes=['*.git', '*.gitignore', '*.gitattributes', '*.log', '__pycache__'])
a.datas += Tree('./src/fonts', prefix='src/fonts', excludes=['*.git', '*.gitignore', '*.gitattributes', '*.log', '__pycache__'])

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CS2-external-cheating',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 禁用控制台输出
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='b.ico'  # 使用项目根目录下的图标文件
)