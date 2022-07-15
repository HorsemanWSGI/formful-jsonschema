from setuptools import setup


setup(
    name='jsonschema_formful',
    install_requires=[
        'formful>=3',
        'jsonschema',
        'jsonref'
    ],
    extras_require={
        'test': [
            'pytest>=3',
            'PyHamcrest'
        ]
    }
)
