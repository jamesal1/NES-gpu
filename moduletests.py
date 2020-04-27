from modules import *


def lin_vs_conv(device="cpu"):
    times = 5
    d = 2 ** 9
    p = 2
    x = 128
    x_sq = x ** 2
    out = 64
    batch_weight = torch.empty(d * x_sq * out, device=device)
    weight = torch.empty(x_sq * out, device=device)
    input = torch.empty(d * p * x_sq, device=device)
    batch_input_linear = input.view(d, x_sq, p)
    batch_input_conv_x = input.view(p, d, x, x)
    batch_input_conv_1 = input.view(p, d * x_sq, 1, 1)
    input_linear = input.view(x_sq, p * d)
    input_conv_x = input.view(p * d, 1, x, x)
    input_conv_1 = input.view(p * d, x_sq, 1, 1)
    batch_weight_linear = batch_weight.view(d, out, x_sq)
    batch_weight_conv_x = batch_weight.view(d * out, 1, x, x)
    batch_weight_conv_1 = batch_weight.view(d * out, x_sq, 1, 1)
    weight_linear = weight.view(out, x_sq)
    weight_conv_x = weight.view(out, 1, x, x)
    weight_conv_1 = weight.view(out, x_sq, 1, 1)
    for _ in range(2):
        for i in range(times):
            torch.cuda.synchronize()
            start = time.time()
            torch.bmm(batch_weight_linear, batch_input_linear)
            torch.cuda.synchronize()
            print("batch_linear", time.time() - start)
        for i in range(times):
            torch.cuda.synchronize()
            start = time.time()
            torch.mm(weight_linear, input_linear)
            torch.cuda.synchronize()
            print("linear", time.time() - start)
        for i in range(times):
            torch.cuda.synchronize()
            start = time.time()
            F.conv2d(batch_input_conv_x, weight=batch_weight_conv_x, groups=d)
            torch.cuda.synchronize()
            print("batch_conv_x", time.time() - start)
        for i in range(times):
            torch.cuda.synchronize()
            start = time.time()
            F.conv2d(input_conv_x, weight=weight_conv_x)
            torch.cuda.synchronize()
            print("conv_x", time.time() - start)
        for i in range(times):
            torch.cuda.synchronize()
            start = time.time()
            F.conv2d(batch_input_conv_1, weight=batch_weight_conv_1, groups=d)
            torch.cuda.synchronize()
            print("batch_conv_1", time.time() - start)
        for i in range(times):
            torch.cuda.synchronize()
            start = time.time()
            F.conv2d(input_conv_1, weight=weight_conv_1)
            torch.cuda.synchronize()
            print("conv_1", time.time() - start)


def randperm_speed(device="cuda"):
    start = time.time()
    m = 256
    n = 256


    for _ in range(20):

        x = torch.empty(m,n, dtype=torch.long)
        w = torch.zeros(n,n, dtype=torch.int32)
        f = torch.zeros(n,n)
        g = torch.zeros(n,n)
        y = torch.empty(m,n)
        a = torch.arange(n)
        b = torch.zeros(n, dtype=torch.long)
        y.random_()
        # f.random_()
        for i in range(m):
            torch.randperm(n, out=x[i])
        a = a.to(device)
        f = f.to(device)
        g = g.to(device)
        w = w.to(device)
        x = x.to(device)
        y = y.to(device)
        b = b.to(device)
        torch.cuda.synchronize()
        start = time.time()
        torch.argsort(x,dim=1)
        z = torch.gather(y, 1, x)
        # for i in range(m):
        #     g+=f[:,x[i]]

        for i in range(m):
            f[b,b] += 1
        print(f.sum())
        torch.mm(f,f)

        # print(w)
        torch.cuda.synchronize()
        # print(y,z)
        print(time.time() - start)


def test_perm(device="cuda"):
    d = 128
    m = 128
    n = 128
    l = PermutedLinear(n,m,d,permutation="out").to(device)
    # l = PermutedLinear(n,m,d).to(device)

    for _ in range(10):
        l.allocate_memory()
        l.set_noise_scale(1.)
        l.set_seed()
        l.set_noise()
        w = torch.rand(d,device=device)
        # w = torch.ones(d,device=device)
        torch.cuda.synchronize()
        start = time.time()
        l.set_grad(w)
        torch.cuda.synchronize()
        print(time.time() - start)

def test_perm_conv(device="cuda"):
    d = 4
    c_in = 5
    c_out = 5
    h = 32
    w = 32
    x = 3
    y = 3
    inp = torch.empty((d, c_in, h, w), device=device)
    inp.normal_()
    l = PermutedConv2d(c_in,c_out,(x,y),d,permutation="both").to(device)
    # l = PerturbedConv2d(c_in,c_out,(x,y),d).to(device)

    for _ in range(10):
        l.allocate_memory()
        l.set_noise_scale(1.)
        l.set_seed()
        l.set_noise()
        w = torch.rand(d,device=device)
        # w = torch.ones(d,device=device)
        torch.cuda.synchronize()
        start = time.time()
        l.perturbed_flag = True
        l.forward(inp)
        l.set_grad(w)
        torch.cuda.synchronize()
        print(time.time() - start)
    for _ in range(10):
        l.allocate_memory()
        l.set_noise_scale(1.)
        l.set_seed()
        l.set_noise()
        w = torch.rand(d,device=device)
        # w = torch.ones(d,device=device)
        torch.cuda.synchronize()
        start = time.time()
        l.perturbed_flag = False
        l.forward(inp)
        # l.set_grad(w)
        torch.cuda.synchronize()
        print("off",time.time() - start)


def time_forward_median(layer, input, times):
    results = []
    for _ in range(times):
        torch.cuda.synchronize()
        start = time.time()
        layer.forward(input)
        torch.cuda.synchronize()
        results += [time.time() - start]
    return sorted(results)[times//2]

def test_linear(device="cuda",times=100):
    for d,m,n in [(1024, 1024, 1024),(1024, 512, 512)]:

        l = PerturbedLinear(n,m,d).to(device)
        sl = SparsePerturbedLinear(n,m,d,sparsity=1).to(device)
        pl = PermutedLinear(n,m,d,permutation="out").to(device)
        for layer, name in [(l,"perturbed"),(sl,"sparse"),(pl,"permuted")]:
            layer.allocate_memory()
            layer.set_noise_scale(1.)
            layer.set_seed()
            layer.set_noise()
            layer.perturbed_flag = True

            inp = torch.rand(d,n,device=device)

            print(name, time_forward_median(layer, inp, times))
        l.perturbed_flag = False
        print("off", time_forward_median(l, inp, times))
        print("naive", d * time_forward_median(l, inp[0], times))





if __name__ == "__main__":
    with torch.no_grad():
        pass
        # speed_test_linear("cuda")
        # speed_test_conv("cuda")
        # lin_vs_conv("cpu")
        # randperm_speed("cuda")
        # sparse_test("cuda")
        # test_perm_conv("cuda")
        test_linear("cuda")
        # test_linear("cuda")
        # test_add("cuda")