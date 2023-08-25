# py-ReverseSemaphoreExclusiveEmpty

A reverse semaphore (also known as a countdown event), with exclusive prioritized empty semaphore execution.
This implementation uses only a single Condition.

## What does that mean?
### Reverse semaphore:
Aquiring the semaphore increments the count.
Releasing the semaphore decrements the count.
Any number of tasks can execute whilst the semaphore is non-zero.

### *Exclusive* empty execution:
Tasks can wait for the semaphore to be empty.
Only one such task can be executing at once. Task execution order is not guaranteed.

### *Prioritized* empty execution:
If a task is waiting for the count to reach zero, then new non-empty waiting tasks will be blocked.

<details>
<summary><h2>Usage</h2></summary>

`async with` is by far the recommended use method (illustrated below), but you can also wrap your code with
```py
await sem.aquire()
...
await sem.release()
```
or
```py
await sem.aquireEmpty()
...
await sem.releaseEmpty()
```
If needed.

Full example code with context managers:
```py
async def nonEmptyTask(id: str, sem: ReverseSemaphoreExclusiveEmpty):
    async with sem.enter():
        print(f"{datetime.now().time()} Task {id} incremented the semaphore to {sem.count} ({sem.emptyWaitersCount} empty waiters)")
        await asyncio.sleep(5)
    print(f"{datetime.now().time()} Task {id} decremented the semaphore to {sem._count} ({sem.emptyWaitersCount} empty waiters)")


async def emptyTask(id: str, sem: ReverseSemaphoreExclusiveEmpty):
    async with sem.enterEmpty():
        print(f"{datetime.now().time()} Empty task {id} entered the semaphore at count {sem._count} ({sem.emptyWaitersCount} empty waiters)")
        await asyncio.sleep(5)
    print(f"{datetime.now().time()} Empty task {id} exited the semaphore at count {sem._count} ({sem.emptyWaitersCount} empty waiters)")


async def main_async():
    sem = ReverseSemaphoreExclusiveEmpty()
    tasks = [
        asyncio.create_task(nonEmptyTask("A", sem)),
        asyncio.create_task(nonEmptyTask("B", sem)),
        asyncio.create_task(emptyTask("C", sem)),
        asyncio.create_task(nonEmptyTask("D", sem)),
        asyncio.create_task(emptyTask("E", sem)),
        asyncio.create_task(emptyTask("F", sem)),
    ]
    await asyncio.wait(tasks)
    print("done")

if __name__ == "__main__":
    asyncio.run(main_async())
```

running the above prints:
```py
22:21:58.892421 Task A incremented the semaphore to 1 (0 empty waiters)
22:21:58.894406 Task B incremented the semaphore to 2 (0 empty waiters)
22:22:03.908709 Task A decremented the semaphore to 1 (3 empty waiters)
22:22:03.908709 Task B decremented the semaphore to 0 (3 empty waiters)
22:22:03.912615 Empty task C entered the semaphore at count 0 (2 empty waiters)
22:22:08.930711 Empty task C exited the semaphore at count 0 (2 empty waiters)
22:22:08.930711 Empty task E entered the semaphore at count 0 (1 empty waiters)
22:22:13.938552 Empty task E exited the semaphore at count 0 (1 empty waiters)
22:22:13.938552 Empty task F entered the semaphore at count 0 (0 empty waiters)
22:22:18.939144 Empty task F exited the semaphore at count 0 (0 empty waiters)
22:22:18.939144 Task D incremented the semaphore to 1 (0 empty waiters)
22:22:23.940605 Task D decremented the semaphore to 0 (0 empty waiters)
done
```
</details>

## Installation

This is not currently a PyPi package. If you would like it added to PyPi, submit an issue and I'll happily publish it.

For now, I use this as a git submodule:
```bash
git submodule init
git submodule add https://github.com/Trimatix/py-ReverseSemaphoreExclusiveEmpty.git reverseSemaphoreExclusiveEmpty
```

And then in python:
```py
from reverseSemaphoreExclusiveEmpty import ReverseSemaphoreExclusiveEmpty
```

It's a shame the name is so long!
