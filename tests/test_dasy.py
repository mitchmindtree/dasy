import dasy
import hy
from boa.contract import VyperContract
import boa

def compile_src(src: str, *args) -> VyperContract:
    return VyperContract(dasy.compile(src), *args)

def compile(filename: str, *args) -> VyperContract:
    with open(filename) as f:
        src = f.read()
        return compile_src(src, *args)

def test_binops():
    src = """
        (defn plus [] :uint256 :external
        (+ 1 2))
    """
    c = compile_src(src)
    assert c.plus() == 3

def test_chain_binops():
    src = """
        (defn plus [] :uint256 :external
        (+ 1 2 3 4 5 6))
    """
    c = compile_src(src)
    assert c.plus() == 21

def test_defvars():
    src = """
    (defvars x :uint256)
    (defn setX [:uint256 x] :external
      (setv self/x x))
    (defn getX [] :uint256 [:external :view] self/x)
    """
    c = get_contract(src)
    c.setX(10)
    assert c.getX() == 10

def test_hello_world():
    c = get_contract("""
    (defvars greet (public (string 100)))
    (defn __init__ [] :external (setv self/greet "Hello World"))
    (defn setGreet [(string 100) x] :external (setv self/greet x))
    """)
    assert c.greet() == "Hello World"
    c.setGreet("yo yo")
    assert c.greet() == "yo yo"

def test_call_internal():
    c = get_contract("""
    (defn _getX [] :uint256 :internal 4)
    (defn useX [] :uint256 :external
      (+ 2 (self/_getX)))
    """)
    assert c.useX() == 6

def test_pure_fn():
    c = get_contract("""
    (defn pureX [:uint256 x] :uint256 [:external :pure] x)
    """)
    assert c.pureX(6) == 6

def test_constructor():
    c = get_contract("""
    (defvars owner (public :address)
            createdAt (public :uint256)
            expiresAt (public :uint256)
            name (public (string 10)))
    (defn __init__ [:uint256 duration] :external
      (setv self/owner msg/sender)
      (setv self/name "z80")
      (setv self/createdAt block/timestamp)
      (setv self/expiresAt (+ block/timestamp
                              duration)))
    """, 100)

    createdAt = c.createdAt()
    expiresAt = c.expiresAt()
    assert expiresAt == createdAt + 100
    assert c.name() == "z80"

def test_if():
    c = get_contract("""
    (defn absValue [:uint256 x y] :uint256 [:external :pure]
      (if (>= x y)
         (return (- x y))
         (return (- y x))))""")
    assert c.absValue(4, 7) == 3

def test_struct():
    c = get_contract("""
    (defstruct Person
        age :uint256)
    (defvars person (public Person))
    (defn __init__ [] :external
      (setv (. self/person age) 12))
    (defn memoryPerson [] Person :external
      (defvar mPers Person self/person)
      (set-in mPers age 10)
      mPers)
    """)
    assert c.person()[0] == 12
    assert c.memoryPerson() == (10,)

def test_arrays():
    c = get_contract("""
    (defvars nums (public (array :uint256 10)))
    (defn __init__ [] :external
      (set-at self/nums 0 5)
      (set-at self/nums 1 10))
    """)
    assert c.nums(0) == 5
    assert c.nums(1) == 10

def test_map():
    c = get_contract("""
    (defvars myMap (public (hash-map :address :uint256))
            owner (public :address))
    (defn __init__ [] :external
      (setv self/owner msg/sender)
      (set-at self/myMap msg/sender 10))
    (defn getOwnerNum [] :uint256 :external
     (get-in self/myMap msg/sender))
    """)
    assert c.myMap("0x8B4de256180CFEC54c436A470AF50F9EE2813dbB") == 0
    assert c.myMap(c.owner()) == 10
    assert c.getOwnerNum() == 10

def test_dynarrays():
    c = get_contract("""
    (defvar nums (public (dyn-array :uint256 3)))
    (defn __init__ [] :external
    (do ;; wrap expressions in do
      (.append self/nums 11)
      (.append self/nums 12)))
    """)
    assert c.nums(0) == 11
    assert c.nums(1) == 12


def test_reference_types():
    c = get_contract("""
    (defvar nums (public (array :uint256 10)))
    (defn __init__ [] :external
      (set-at self/nums 0 123)
      (set-at self/nums 9 456)
      (defvar arr (array :uint256 10) self/nums))
    (defn memoryArrayVal [] '(:uint256 :uint256) :external
      (defvar arr (array :uint256 10) self/nums)
      (set-at arr 1 12)
      '((get-in arr 0) (get-in arr 1)))
    """)
    assert c.nums(0) == 123
    assert c.nums(1) == 0
    assert c.memoryArrayVal() == (123, 12)
