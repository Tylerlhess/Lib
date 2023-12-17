''' 
usually we use threads, because we typically have few but in some cases where we
need to scale the number of simple concurrent operations we can use asyncio.
yet the main thread is not run as an asyncio event loop, so we need to set up a
dedicated thread just for that.
'''
import inspect
import asyncio
import threading


class AsyncThread():

    def __init__(self):
        self.loop = None
        self._runForever()

    def startAsyncEventLoop(self):
        ''' runs in a separate thread and maintains the async event loop '''
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    def cancelTask(self, future):
        ''' cancels the given asyncio.Future task '''
        if future is not None and not future.done():
            future.cancel()

    async def asyncWrapper(self, func: callable, *args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Handle or log the exception as needed
            print(f'Exception in asyncWrapper: {e}')
            raise

    async def repeatWrapper(self, func: callable, interval: float, *args, **kwargs):
        if isinstance(interval, int):
            interval = float(interval)
        while True:
            try:
                await asyncio.sleep(interval)
                await self.asyncWrapper(func, *args, **kwargs)
            except asyncio.CancelledError:
                # Handle cancellation
                break
            except Exception as e:
                # Handle or log the exception
                print(f'Exception in repeatWrapper: {e}')

    async def delayedWrapper(self, func: callable, delay: float, *args, **kwargs):
        if isinstance(delay, int):
            delay = float(delay)
        if isinstance(delay, float):
            await asyncio.sleep(delay)
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f'Exception in delayedWrapper: {e}')
            raise

    def _preRun(self, task: callable = None, delay: float = None, interval: float = None, *args, **kwargs):
        if self.loop is None:
            self._runForever()
        if self.loop is None:
            raise Exception('Event loop is not running.')
        if inspect.iscoroutinefunction(task):
            coroutine = task(*args, **kwargs)
        elif inspect.isfunction(task) or inspect.ismethod(task):
            if delay is not None:
                coroutine = self.delayedWrapper(task, delay, *args, **kwargs)
            elif interval is not None:
                coroutine = self.repeatWrapper(task, interval, *args, **kwargs)
            else:
                coroutine = self.asyncWrapper(task, *args, **kwargs)
        else:
            raise TypeError('Task must be an async or a regular function.')
        return coroutine

    def runAsync(self, task: callable = None, *args, **kwargs):
        ''' submits async task or function to the event loop '''
        return self._runAsync(self._preRun(task, *args, **kwargs))

    def delayedRun(self, task: callable = None, delay: float = 5, *args, **kwargs):
        ''' submits async tasks to the event loop with a delay '''
        return self._runAsync(self._preRun(task, delay, *args, **kwargs))

    def repeatRun(self, task: callable, interval: float = 60, *args, **kwargs):
        return self._runAsync(self._preRun(task, interval=interval, *args, **kwargs))

    def _runAsync(self, coroutine: callable):
        ''' submits async task or function to the event loop '''
        return asyncio.run_coroutine_threadsafe(coroutine, self.loop)

    def _runForever(self):
        thread = threading.Thread(target=self.startAsyncEventLoop, daemon=True)
        thread.start()


# from concurrent.futures import Future

# Submitting a task to the async thread
# future = asyncThread.delayedRun(sample_function, 5, "Hello")

# Example of an async function
# async def asyncTask(self):
#    # Your async code here
#    print("Async task executed")
#    await asyncio.sleep(1)

# Submitting tasks to the async loop from the main thread
# future = run_async(asyncTask())

# Optional: wait for the task to complete, or you can continue with your main program
# result = future.result()
