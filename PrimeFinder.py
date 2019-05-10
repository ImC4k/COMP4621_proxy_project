'''
provide prime number related functions
'''

def factorize(number):
    factors = []
    for i in range(1, number + 1):
        if number % i == 0:
            factors.append(i)
    return factors

def isPrime(number):
    return len(factorize(number)) == 2

def findNextPrime(number):
    number += 1
    while not isPrime(number):
        number += 1
    return number
