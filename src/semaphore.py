from asyncio import Condition
from contextlib import AbstractAsyncContextManager
from types import TracebackType
from typing import Optional, Type


class _ReverseSemaphoreEmptyContext(AbstractAsyncContextManager):
    def __init__(self, sem: "ReverseSemaphoreExclusiveEmpty") -> None:
        self.sem = sem


    async def __aenter__(self):
        await self.sem.aquireEmpty()
    

    async def __aexit__(self, __exc_type: Optional[Type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        await self.sem.releaseEmpty()
    

class _ReverseSemaphoreNonEmptyContext(AbstractAsyncContextManager):
    def __init__(self, sem: "ReverseSemaphoreExclusiveEmpty") -> None:
        self.sem = sem


    async def __aenter__(self):
        await self.sem.aquire()
    

    async def __aexit__(self, __exc_type: Optional[Type[BaseException]], __exc_value: Optional[BaseException], __traceback: Optional[TracebackType]) -> Optional[bool]:
        await self.sem.release()


class ReverseSemaphoreExclusiveEmpty:
    """A reverse semaphore (also known as a countdown event), with exclusive prioritized empty semaphore execution.

    Explanation of those terms...

    Reverse semaphore:
    Aquiring the semaphore increments the count.
    Releasing the semaphore decrements the count.
    Any number of tasks can execute whilst the semaphore is non-zero.
    
    *Exclusive* empty execution:
    Tasks can wait for the semaphore to be empty.
    Only one such task can be executing at once. Task execution order is not guaranteed.

    *Prioritized* empty execution:
    If a task is waiting for the count to reach zero, then new non-empty waiting tasks will be blocked.

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
    """

    def __init__(self) -> None:
        self._count = 0
        self._emptyWaitersCount = 0
        self._cond = Condition()


    @property
    def count(self):
        """The current semaphore count.
        """
        return self._count
    

    @property
    def emptyWaitersCount(self):
        """The number of tasks currently waiting for the semaphore to be empty.
        """
        return self._emptyWaitersCount

    
    async def aquire(self):
        """Wait for there to be no empty-executing tasks, and then increment the semaphore.
        """
        async with self._cond:
            await self._cond.wait_for(lambda: self._emptyWaitersCount == 0)
            self._count += 1


    async def release(self):
        """decrement the semaphore.
        """
        async with self._cond:
            self._count -= 1
            self._cond.notify()


    async def aquireEmpty(self):
        """Wait for there to be no non-empty-executing tasks, and then aquire exclusivity.
        """
        self._emptyWaitersCount += 1
        try:
            async with self._cond:
                await self._cond.wait_for(lambda: self._count == 0)
        finally:
            self._emptyWaitersCount -= 1


    async def releaseEmpty(self):
        """Release exclusivity to another empty-executing task, or a non-empty-executing task if there are none.
        """
        async with self._cond:
            self._cond.notify()


    def enter(self):
        """Aquire the semaphore as a context, and release it on exit.
        use this method with `async with`:

        ```py
        async with sem.enter():
            ...
        ```

        Assuming no exceptions are raised etc, this is analagous to:
        ```py
        await sem.aquire()
        ...
        await sem.release()
        """
        return _ReverseSemaphoreNonEmptyContext(self)


    def enterEmpty(self):
        """Aquire the semaphore when empty as a context, and release it on exit.
        use this method with `async with`:

        ```py
        async with sem.enterEmpty():
            ...
        ```

        Assuming no exceptions are raised etc, this is analagous to:
        ```py
        await sem.aquireEmpty()
        ...
        await sem.releaseEmpty()
        """
        return _ReverseSemaphoreEmptyContext(self)
