from setuptools import setup, find_packages

with open('requirements.txt') as f:
    install_requires = f.read().strip().split('\n')

setup(
    name='pos_restaurant_itb',
    version='1.0.0',
    description='POS Restaurant Management App for ERPNext',
    author='PT. Innovasi Terbaik Bangsa',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=install_requires,
    license='MIT'
)