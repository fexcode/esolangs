import re

class Compiler(object):

    def parse(self):
        i = 0
        while i < len(self.code):
            j = i
            code = self.code[i:]
            for r, op in self.regexs.items():
                match = re.match(r, code)
                if match:
                    d = {'start':i, 'next':i+match.end(), 'op': op, 'exp': match.group()}
                    if any(match.groups()):
                        d['arg'] = match.groups()[0]
                    i += match.end()
                    yield d
            if j == i:
                i+=1
                raise Exception('parse failed')

    def __init__(self, code):
        self.code = code
        self.regexs = {
            '^\t\n  ': 'output_char',
            '^\t\n \t': 'output_number',
            '^\t\n\t ': 'read_chr',
            '^\t\n\t\t': 'read_num',
            '^  ([^\n]+)\n': 'append',
            '^ \t ([^\n]+)\n': 'dup_at',
            '^ \t\n([^\n]+)\n': 'pop_x',
            '^ \n ': 'dupe',
            '^ \n\t': 'swap',
            '^ \n\n': 'pop',
            '^\t   ': 'add',
            '^\t  \t': 'sub',
            '^\t  \n': 'mul',
            '^\t \t ': 'div',
            '^\t \t\t': 'mod',
            '^\n  ([^\n]*\n)': 'mark_sub',
            '^\n \t([^\n]*\n)': 'call_sub',
            '^\n \n([^\n]*\n)': 'jmp',
            '^\n\t ([^\n]*\n)': 'jmp_eq',
            '^\n\t\t([^\n]*\n)': 'jmp_lt',
            '^\n\t\n': 'exit_sub',
            '^\n\n\n': 'terminate',
            '^\t\t ': 'heap_store', 
            '^\t\t\t': 'heap_retrieve'
        }

class Interpreter(object):
    def parse_number(self):
        start = self.ip
        s_bin = ''
        sign = self.npsc[self.code[self.ip]]
        if sign is str:
            raise Exception('bad sign')
        self.ip += 1
        
        while self.code[self.ip] != '\n':
            s_bin += self.npbc[self.code[self.ip]]
            self.ip += 1
        self.ip+=1

        return int(s_bin, 2) * sign if s_bin != '' else 0

    def swap(self):
        self.stack[-1],self.stack[-2] = self.stack[-2],self.stack[-1]
        return 'swap'

    def output_number(self):
        self.output += str(self.stack.pop())  
        return 'output_number'

    def output_char(self):
        cur = self.stack.pop()
        if type(cur) is int:
            self.output += chr(cur)
        else:
            self.output += cur 
        return 'output_char'

    def terminate(self):
        self.ip = len(self.code)
        self.terminated = True
        return 'term'

    def dup_at(self):
        parsed = self.parse_number() + 1
        if parsed <= 0 or parsed > len(self.stack):
            raise Exception('Out of bounds')
        self.stack.append(self.stack[-parsed])
        return 'dup_at'

    def append(self):
        self.stack.append(self.parse_number())
        return 'append read'

    def pop_x(self):
        x = self.parse_number()
        
        top = self.stack.pop()
        if x > len(self.stack) or x < 0:
            x = len(self.stack)

        for _ in range(x):
            self.stack.pop()
        self.stack.append(top)

        return 'pop_x'

    def heap_store(self):
        a = self.stack.pop()        
        b = self.stack.pop() 
        self.heap[b] = a
        return 'heap store'


    def heap_retrieve(self):
        a = self.stack.pop()
        self.stack.append(self.heap[a])
        return 'heap ret'

    def add(self):
        a,b = self.stack.pop(), self.stack.pop()
        self.stack.append(b+a)
        return 'add'
    
    def sub(self):
        a,b = self.stack.pop(), self.stack.pop()
        self.stack.append(b-a)
        return 'sub'
    
    def mul(self):
        a,b = self.stack.pop(), self.stack.pop()
        self.stack.append(b*a)
        return 'mul'

    def div(self):
        a,b = self.stack.pop(), self.stack.pop()
        self.stack.append(b//a)
        return 'div'

    def mod(self):
        a,b = self.stack.pop(), self.stack.pop()
        self.stack.append(b%a)
        return 'mod'

    def read_chr(self):
        self.heap[self.stack.pop()] = self.input[self.inp]
        self.inp+=1
        return 'read_chr'
    
    def read_num(self):
        remaining = self.input[self.inp:]
        index = remaining.find('\n')
        val = int(remaining[:index])
        self.heap[self.stack.pop()] = val
        self.inp+=index+1

        return 'read_num'

    def mark_sub(self):
        code = self.code[self.ip:]
        label = code[:code.find('\n')+1]
        self.subroutines[label] = self.ip+len(label) # +1 ??
        self.ip+= len(label)
        return 'mark_sub'

    def call_sub(self):
        code = self.code[self.ip:]
        label = code[:code.find('\n')+1]
        self.call_stack.append(self.ip+len(label))
        self.ip = self.subroutines[label]    
        return 'call_sub'

    def exit_sub(self):
        self.ip = self.call_stack.pop()
        return 'exit_sub'

    def jmp(self): 
        code = self.code[self.ip:]
        label = code[:code.find('\n')+1]
        self.ip = self.subroutines[label]
        return 'jmp'

    def jmp_eq(self):
        if self.stack.pop() == 0:
            self.jmp()
        else:
            self.ip += 1
        return 'jmp_eq'

    def jmp_lt(self):
        if self.stack.pop() < 0:
            self.jmp()
        else:
            self.ip += 1
        return 'jmp_lt'


    def __init__(self, code, input):
        def only_whitespace(s):
            return ''.join([c for c in s if c in ' \t\n'])

        self.code = only_whitespace(code)
        self.input = input
        self.ip = 0
        self.inp = 0
        self.stack = []
        self.call_stack = []
        self.heap = {}
        self.subroutines = {}
        self.output = ''
        self.terminated = False

        labels = list([d for d in Compiler(self.code).parse() if d['op'] == 'mark_sub'])
        for label in labels:
            if label['arg'] in self.subroutines:
                raise Exception('Doublely Declared Label')
            self.subroutines[label['arg']] = label['next']

        self.ioc = {
            '  ': self.output_char,
            ' \t': self.output_number,
            '\t ': self.read_chr,
            '\t\t': self.read_num
        }

        self.smc = {
            ' ': self.append,
            '\n ': lambda: self.stack.append(self.stack[-1]),
            '\t\n': self.pop_x,
            '\t ': self.dup_at,
            '\n\t': self.swap,
            '\n\n': self.stack.pop
        }
        self.ac = {
            '  ': self.add,
            ' \t': self.sub,
            ' \n': self.mul,
            '\t ': self.div,
            '\t\t': self.mod
        }
        self.fcc = {
            '  ': self.mark_sub,
            ' \t': self.call_sub,
            ' \n': self.jmp,
            '\t ': self.jmp_eq,
            '\t\t': self.jmp_lt,
            '\t\n': self.exit_sub,
            '\n\n': self.terminate 
        }

        # HEAP
        self.hac = {
            ' ': self.heap_store, 
            '\t': self.heap_retrieve
        }

        self.imp = {
            '\t\n': self.ioc,
            '\t ': self.ac,
            '\t\t': self.hac,
            '\n': self.fcc,
            ' ': self.smc,
        }

        self.npsc = {'\t': -1, ' ': 1, '\n': '\n'}
        self.npbc = {'\t': '1', ' ': '0', '\n': '\n'}

        regexs = {
            '\t\n  ': self.output_char,
            '\t\n \t': self.output_number,
            '\t\n\t ': self.read_chr,
            '\t\n\t\t': self.read_num,
            '  ([^\n]+)\n': self.append,
            ' \t ([^\n]+)\n': self.dup_at,
            ' \t\n([^\n]+)\n': self.pop_x,
            ' \n ': lambda: self.stack.append(self.stack[-1]),
            ' \n\t': self.swap,
            ' \n\n': self.stack.pop,
            '\t   ': self.add,
            '\t  \t': self.sub,
            '\t  \n': self.mul,
            '\t \t ': self.div,
            '\t \t\t': self.mod,
            '\n  ([^\n]*\n)': self.mark_sub,
            '\n \t([^\n]*\n)': self.call_sub,
            '\n \n([^\n]*\n)': self.jmp,
            '\n\t ([^\n]*\n)': self.jmp_eq,
            '\n\t\t([^\n]*\n)': self.jmp_lt,
            '\n\t\n': self.exit_sub,
            '\n\n\n': self.terminate,
            '\t\t ': self.heap_store, 
            '\t\t\t': self.heap_retrieve
        }

    def parse(self):
        while self.ip < len(self.code):
            imp1 = self.code[self.ip:self.ip + 2]
            for iden, lookup in self.imp.items():
                if imp1.startswith(iden):
                    oip = self.ip
                    self.ip += len(iden)
                    imp2 = self.code[self.ip:self.ip + 2]
                    for jden, definition in lookup.items():
                        if imp2.startswith(jden):
                            self.ip += len(jden)
                            out = definition()
                            break
                    break
        if not self.terminated:
            raise Exception('not terminated')

# solution
def whitespace(code, inp=''):
    interpreter = Interpreter(code, inp)
    interpreter.parse()
    return interpreter.output

def main():
    code = ''''''
    print(whitespace(code))

main()