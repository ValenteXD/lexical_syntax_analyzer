from inter.expr import *
from symbols.array import *
from symbols.env import *
from symbols.type import *
import sys


class Parser:
    __lex = None
    __look = None
    top = None
    enclosing = False

    def __init__(self, l):
        self.__lex = l
        self.move()

    def move(self):
        self.__look = self.__lex.scan()

    def error(self, s):
        print()
        print(f'near line {str(self.__lex.line)}: {s}')
        sys.exit()

    def match(self, t):
        if self.__look.tag == t:
            self.move()
        else:
            self.error(f'syntax error, expected {str(t)}, got "{str(self.__look.lexeme)}"')

    def set_check(self, p1, p2):
        if Type.numeric(p1, p1) and Type.numeric(p2, p2):
            return p2
        elif p1 == BOOL and p2 == BOOL:
            return p2
        else:
            return None

    def set_elemcheck(self, p1, p2):
        if isinstance(p1, Array) or isinstance(p2, Array):
            return None
        elif p1 == p2:
            return p2
        elif Type.numeric(p1, p1) and Type.numeric(p2, p2):
            return p2
        else:
            return None

    def program(self):
        if self.__look.tag == Tag.DEFINE:
            self.func()

    def func(self):
        self.match(Tag.DEFINE)
        self.match(Tag.BASIC)
        self.match(Tag.ID)
        self.match('(')
        saved_env = self.top
        self.top = Env(self.top)
        self.decls()
        self.match(')')
        self.block()
        self.top = saved_env
        self.program()

    def block(self):
        self.match(Tag.BEGIN)
        saved_env = self.top
        self.top = Env(self.top)
        self.decls()
        self.stmts()
        self.match(Tag.END)
        self.top = saved_env
        self.program()

    def decls(self):
        while self.__look.tag == Tag.BASIC:
            p = self.type_()
            tok = self.__look
            self.match(Tag.ID)
            self.match(';')
            id_ = Expr(tok, p)
            self.top.put(tok, id_)

    def type_(self):
        p = self.__look
        self.match(Tag.BASIC)

        if self.__look.tag != '[':
            return p
        else:
            return self.dims(p)

    def dims(self, p):
        self.match('[')
        self.match(Tag.NUM)
        self.match(']')

        if self.__look.tag == '[':
            p = self.dims(p)

        return Array(p)

    def stmts(self):
        if self.__look.tag != Tag.END:
            self.stmt()
            self.stmts()

    def stmt(self):
        if self.__look.tag == ';':
            self.move()

        elif self.__look.tag == Tag.BASIC:
            self.decls()

        elif self.__look.tag == Tag.IF:
            self.match(Tag.IF)
            self.match('(')
            x = self.bool_()
            self.match(')')
            self.stmt()

            if x.type_ != BOOL:
                self.error('boolean required in if')

            if self.__look.tag == Tag.ELSE:
                self.match(Tag.ELSE)
                self.stmt()

        elif self.__look.tag == Tag.WHILE:
            saved_stmt = self.enclosing
            self.enclosing = True
            self.match(Tag.WHILE)
            self.match('(')
            x = self.bool_()
            self.match(')')
            self.stmt()

            if x.type_ != BOOL:
                self.error('boolean required in while')

            self.enclosing = saved_stmt

        elif self.__look.tag == Tag.DO:
            saved_stmt = self.enclosing
            self.match(Tag.DO)
            self.stmt()
            self.match(Tag.WHILE)
            self.match('(')
            x = self.bool_()
            self.match(')')
            self.match(';')

            if x.type_ != BOOL:
                self.error('boolean required in do')

            self.enclosing = saved_stmt

        elif self.__look.tag == Tag.SWITCH:
            saved_stmt = self.enclosing
            self.enclosing = True
            self.match(Tag.SWITCH)
            self.match('(')
            x = self.bool_()
            self.match(')')
            self.stmt()

            if x.type_ != NUM:
                self.error('number required in switch')

            self.enclosing = saved_stmt

        elif self.__look.tag == Tag.CASE:
            saved_stmt = self.enclosing
            self.enclosing = True
            self.match(Tag.CASE)
            self.match('(')
            x = self.bool_()
            self.match(')')
            self.stmt()

            if x.type_ != NUM:
                self.error('number required in case')
            
            self.enclosing = saved_stmt


        elif self.__look.tag == Tag.BREAK:
            self.match(Tag.BREAK)
            self.match(';')

            if not self.enclosing:
                self.error('unenclosed break')

        elif self.__look.tag == Tag.PRINT:
            self.match(Tag.PRINT)
            t = self.__look

            if t.tag == Tag.ID:
                self.match(Tag.ID)
                id_ = self.top.get(t)

                if not id_:
                    self.error(f'{t.toString()} undeclared')

            self.match(';')

        elif self.__look.tag == Tag.READ:
            self.match(Tag.READ)
            t = self.__look
            self.match(Tag.ID)
            id_ = self.top.get(t)

            if not id_:
                self.error(f'{t.toString()} undeclared')

            self.match(';')

        elif self.__look.tag == Tag.BEGIN:
            self.block()

        elif self.__look.tag == Tag.RETURN:
            self.match(Tag.RETURN)
            self.bool_()
            self.match(';')

        else:
            self.assign()

    def assign(self):
        t = self.__look
        self.match(Tag.ID)
        id_ = self.top.get(t)

        if not id_:
            self.move()

            if self.__look.tag == Tag.NUM:
                id_ = Expr(t, NUM)
            elif self.__look.tag == Tag.REAL:
                id_ = Expr(t, REAL)
            elif self.__look.tag == CHAR:
                id_ = Expr(t, CHAR)
            elif self.__look.tag in [Tag.TRUE, Tag.FALSE]:
                id_ = Expr(t, BOOL)

            self.top.put(t, id_)
            y = self.bool_()

            if not self.set_check(id_.type_, y.type_):
                self.error('type error')

            self.match(';')

        elif self.__look.tag == '=':
            self.move()
            y = self.bool_()

            if not self.set_check(id_.type_, y.type_):
                self.error('type error')

            self.match(';')

        else:
            x = self.offset(id_)
            self.match('=')
            y = self.bool_()

            if not self.set_elemcheck(x.type_, y.type_):
                self.error('type error')

            self.match(';')

    def bool_(self):
        x = self.join()

        while self.__look.tag == Tag.OR:
            tok = self.__look
            self.move()
            self.join()
            x = Expr(tok, BOOL)

        return x

    def join(self):
        x = self.equality()

        while self.__look.tag == Tag.AND:
            tok = self.__look
            self.move()
            self.equality()
            x = Expr(tok, BOOL)

        return x

    def equality(self):
        x = self.rel()

        while self.__look.tag in [Tag.EQ, Tag.NE]:
            tok = self.__look
            self.move()
            self.rel()

            return Expr(tok, BOOL)

        return x

    def rel(self):
        x = self.expr()

        if self.__look.tag in ['<', Tag.LE, Tag.GE, '>']:
            tok = self.__look
            self.move()
            y = self.expr()
            type_ = Type.max(x.type_, x.type_, y.type_)

            if not type_:
                self.error('type error')

            return Expr(tok, BOOL)

        else:
            return x

    def expr(self):
        x = self.term()

        while self.__look.tag in ['+', '-']:
            self.move()
            y = self.term()
            type_ = Type.max(x.type_, x.type_, y.type_)

            if not type_:
                self.error('type error')

        return x

    def term(self):
        x = self.unary()

        while self.__look.tag in ['*', '/']:
            self.move()
            y = self.unary()
            type_ = Type.max(x.type_, x.type_, y.type_)

            if not type_:
                self.error('type error')

        return x

    def unary(self):
        if self.__look.tag == '-':
            self.move()
            x = self.unary()
            type_ = Type.max(x.type_, NUM, x.type_)

            if not type_:
                self.error('type error')

        elif self.__look.tag == Tag.NOT:
            tok = self.__look
            self.move()
            self.unary()

            return Expr(tok, BOOL)

        else:
            return self.factor()

    def factor(self):
        x = None

        if self.__look.tag == '(':
            self.move()
            x = self.bool_()
            self.match(')')

            return x

        elif self.__look.tag == Tag.NUM:
            x = Expr(Num(self.__look), NUM)
            self.move()

            return x

        elif self.__look.tag == Tag.REAL:
            x = Expr(Num(self.__look), REAL)
            self.move()

            return x

        elif self.__look.tag == Tag.TRUE:
            x = true
            self.move()

            return x

        elif self.__look.tag == Tag.FALSE:
            x = false
            self.move()

            return x

        elif self.__look.tag == Tag.ID:
            id_ = self.top.get(self.__look)

            if not id_:
                self.error(f'{self.__look.toString()} undeclared')

            self.move()

            if self.__look.tag != '[':
                return id_
            else:
                return self.offset(id_)

        else:
            self.error(f'syntax error, expected a factor, got "{str(self.__look.tag)}"')

            return x

    def offset(self, a):
        type_ = a.type_
        self.match('[')
        self.bool_()
        self.match(']')
        type_ = type_.of

        while self.__look.tag == '[':
            self.match('[')
            self.bool_()
            self.match(']')
            type_ = type_.of

        return Expr(Word('[]', Tag.INDEX), type_)
