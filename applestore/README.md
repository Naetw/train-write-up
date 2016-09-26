# applestore

## 前言
這題花了蠻久時間才解出來，中間試了好幾種方法來控制 EIP，所以紀錄一下好了

## 解題過程

先用 `objdump` 觀察一下用了哪些 function，看到了：

	080484d0 <alarm@plt>:

於是先 patch，把 `alarm` 改成 `isnan` 比較好測試：

~~~vim
:%s/alarm/isnan/g
~~~

稍微看了一下程式在幹嘛，大概有以下功能：

1. list() 列出可以買的商品
2. add() 選擇一樣商品，他會 call create() 這個 function，他會 `malloc`一塊空間然後把商品名稱的 pointer 放在第一格，第二格則放價錢，call 完 create() 後會 call insert()，此程式在 global buffer 有一個 variable - **myCart**，在他的第三格存著商品的 heap address，就像 linked list 一樣，而且是 double linked list，每個商品的 heap 都有 FD 跟 BK，簡單來說 insert() 這個  function 就是在把這些 node 連接起來。
3. delete() 這題 `malloc` 出來的空間並不會回收，他只有對前面提到的 **myCart** 串起來的 list 做手工 `unlink`，而這也是這題的重點。
4. cart() 就把目前在購物車裡的東西都 dump 出來
5. checkout() 這裡有特別的商品 **iphone8**，當你前面放進購物車裡的商品價格全部加起來有 7174 就可以把這個 **iphone8** 也放進購物車，這也是這題的切入口，因為裡面他是把一個 **stack address** insert 進去 list 裡，而這個 stack address 也是我們在 handler() 中隨便選擇的一個 function 進行 `read` 的時候可以寫到的地方。

所以為了得到 **iphone8**，算了一下數學QQ，最後出來是需要 `18*119 + 229 + 2*399 + 5*499` 這麼多的手機，才能拿 **iphone8**

好了拿到 **iphone8** 之後就可以開始 leak information 了！首先是來 `read` 讀上去的 buffer memory layout:

~~~python
	+---------+
	|    |xxxx|   buffer start(2 bytes)
	-----------
	|xxxxxxxxx|   name(myCart 串起來的 double linked list 就是串接到這)(4 bytes)
	-----------
	|xxxxxxxxx|   price(4 bytes)
	-----------
	|xxxxxxxxx|   FD(4 bytes)
	-----------
	|xxxxxxxxx|   BK(4 bytes)
	+---------+
~~~

其實可以讀 21 bytes 但是 BK 後面就不是那麼重要就不畫了。

由 cart() 會 dump 出商品名字還有價錢等等，我們利用這個來 leak libc function 的 libc address。

這邊 payload：

~~~python
atoi_got = 0x0804b040
r.sendline('4')
sleep(0.1)
r.sendline('y' + '\x00' + p32(atoi_got) + p32(0x1))
r.recvuntil('26:')
r.recvuntil('27: ')
x = r.recvuntil('-')
atoi = u32(x[:4])
print hex(atoi)
~~~

在這邊可以 leak 出 libc function address，再利用題目給的 `libc.so` 可以拿到 libc base address，接下來還需要再 leak 一個東西 --- `stack address`

之前比賽有遇到需要 leak stack address 的題目，**pwn queen meh** 說過 libc 裡有一個 `environ` symbol，裡面存著 stack address，所以拿到這個 `environ` 的 address 後，做跟上面一樣的事，來 leak stack address。payload 如下：

~~~python
r.sendline('4')
r.recvrepeat(0.1)
r.sendline('y' + '\x00' + p32(environ) + p32(0x1))
r.recvuntil('26:')
r.recvuntil('27: ')
x = r.recvuntil('-')
stack = u32(x[:4])
print hex(stack)
~~~

leak 完之後就需要 利用 `unlink` 來控制 EIP 了，在這裡我嘗試各種方法，直接把 `atoi` 的 GOT 寫成 `system`，但是因為 unlink 的 side effect --- BK->fd = FD，所以不能直接這樣搞，後來想要搬 ebp，讓程式 ret 到我想要的地方，但是 call 完 delete() 之後又會做一些事所以其實這招也不行。

後來的解法是把 ebp 搬到 GOT table 上，讓他在 call 完 delete() 之後又要再讀一次 cmd 的時候，把 `atoi` 寫掉 而前面的 cmd 放 `sh\x00'` 讀完後，到 call `atoi` 時候可以變成 `system('sh')`，就拿得到 shell 了。
