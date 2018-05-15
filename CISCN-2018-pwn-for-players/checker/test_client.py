import my_client
import random
import time

SYMBOLS = [
    '+',
    '-',
    '*',
    '/',
]

def test_case(func):
    def inner_func(*args, **kwargs):
        print('running %s' % func.__name__)
        func(*args, **kwargs)
    return inner_func

def rand():
    return random.randint(0, 1231211)


def gen_add_expr():
    return '{} + {}'.format(
        rand(),
        rand()
    )


def gen_random_expr():
    expr = str(rand())
    for i in range(random.randint(0, 10)):
        expr += '{} {}'.format(
            random.choice(SYMBOLS),
            rand()
        )
    return expr


@test_case
def basic_test():
    client = my_client.RpcClient('localhost')
    expr = '{} * {} + {} - {} * ({} + {})'.format(
        rand(),
        rand(),
        rand(),
        rand(),
        rand(),
        rand(),
    )
    res = client.call(expr)
    assert(res == int(eval(expr)))
    client.close()


@test_case
def basic_queue_test():
    client = my_client.RpcClient('localhost')
    expr1 = gen_add_expr()
    expr2 = gen_add_expr()
    id1 = client.call_request(expr1)
    id2 = client.call_request(expr2)
    time.sleep(3)
    try:
        client.try_retrieve(id2)
        assert(False)
    except my_client.RpcPacketUnavailableException:
        pass
    res = client.try_retrieve(id1)
    assert(int(res.result_bytes) == eval(expr1))
    res = client.try_retrieve(id2)
    assert(int(res.result_bytes) == eval(expr2))
    client.close()


@test_case
def random_queue_test(client=None):
    if client is None:
        client = my_client.RpcClient('localhost')
    queue = []
    for i in range(random.randint(5, 20)):
        if random.random() < 0.25 and len(queue) > 0:
            time.sleep(1)
            cur_head = queue[0]
            cur_id = cur_head[0]
            cur_expr = cur_head[1]
            print(cur_expr)
            res = client.try_retrieve(cur_id)
            assert(int(res.result_bytes) == eval(cur_expr))
            queue = queue[1:]
        else:
            expr = gen_random_expr()
            queue.append((client.call_request(expr), expr.replace('/', '//')))
    while len(queue) > 0:
        time.sleep(1)
        cur_head = queue[0]
        cur_id = cur_head[0]
        cur_expr = cur_head[1]
        res = client.try_retrieve(cur_id)
        assert(int(res.result_bytes) == eval(cur_expr))
        queue = queue[1:]

    client.close()


def random_queue_stoppable_test(client=None):
    if client is None:
        client = my_client.RpcClient('localhost')
    queue = []
    for i in range(random.randint(5, 20)):
        if random.random() < 0.5:
            yield
        if random.random() < 0.25 and len(queue) > 0:
            time.sleep(1)
            cur_head = queue[0]
            cur_id = cur_head[0]
            cur_expr = cur_head[1]
            print(cur_expr)
            res = client.try_retrieve(cur_id)
            assert(int(res.result_bytes) == eval(cur_expr))
            queue = queue[1:]
        else:
            expr = gen_random_expr()
            queue.append((client.call_request(expr), expr.replace('/', '//')))
    while len(queue) > 0:
        time.sleep(1)
        cur_head = queue[0]
        cur_id = cur_head[0]
        cur_expr = cur_head[1]
        res = client.try_retrieve(cur_id)
        assert(int(res.result_bytes) == eval(cur_expr))
        queue = queue[1:]

    client.close()


@test_case
def seperated_provider_test():
    client1 = my_client.RpcClient('localhost')
    client2 = my_client.RpcClient('localhost')
    random_queue_test(client1)
    random_queue_test(client2)


@test_case
def crossed_provider_test():
    client1 = my_client.RpcClient('localhost')
    client2 = my_client.RpcClient('localhost')
    test1 = random_queue_stoppable_test(client1)
    test2 = random_queue_stoppable_test(client2)
    next(test1)
    next(test2)

    stop1 = False
    stop2 = False
    while not stop1 or not stop2:
        if not stop1:
            try:
                print('executing thread1')
                next(test1)
            except StopIteration:
                stop1 = True
        if not stop2:
            try:
                print('executing thread2')
                next(test2)
            except StopIteration:
                stop2 = True


def test_all():
    basic_test()
    basic_queue_test()
    random_queue_test()
    seperated_provider_test()
    crossed_provider_test()

if __name__ == '__main__':
    test_all()
