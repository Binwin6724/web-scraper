from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from web_scraper.src.web_scraper.tools.image_summarizer_tool import ImageSummarizerTool
from dotenv import load_dotenv

load_dotenv()

# If you want to run a snippet of code before or after the crew starts, 
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class ImageSummarizerCrew():  # Renamed class to avoid conflicts
	"""ImageSummarizer crew"""

	agents_config = 'config/agents.yaml'
	tasks_config = 'config/tasks.yaml'

	# If you would like to add tools to your agents, you can learn more about it here:
	# https://docs.crewai.com/concepts/agents#agent-tools
	@agent
	def image_summarizer(self) -> Agent:
		return Agent(
			config=self.agents_config['image_summarizer'],
			tools=[ImageSummarizerTool()],
			verbose=True
		)

	# To learn more about structured task outputs, 
	# task dependencies, and task callbacks, check out the documentation:
	# https://docs.crewai.com/concepts/tasks#overview-of-a-task
	@task
	def image_summarization_task(self) -> Task:
		return Task(
			config=self.tasks_config['image_summarization_task'],
		)

	@crew
	def crew(self) -> Crew:
		"""Creates the ImageSummarizer crew"""
		# To learn how to add knowledge sources to your crew, check out the documentation:
		# https://docs.crewai.com/concepts/knowledge#what-is-knowledge

		return Crew(
			agents=self.agents, # Automatically created by the @agent decorator
			tasks=self.tasks, # Automatically created by the @task decorator
			process=Process.sequential,
			verbose=True,
			# process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
		)
