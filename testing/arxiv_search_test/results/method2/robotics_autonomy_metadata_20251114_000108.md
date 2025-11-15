# Search Results: method2 - Technological advancements in robotics and autonomous systems

Test run at: 2025-11-14 00:01:08

## Test Parameters

- **Method**: method2
- **Test ID**: robotics_autonomy
- **Topics**: Robotics and autonomy
- **Queries**: Autonomous navigation systems, Robotic manipulation techniques, best techniques in robotics
- **Total Results**: 20 papers

## Papers

### 1. Artificial Intelligence for Long-Term Robot Autonomy: A Survey

- **Authors**: Lars Kunze, Nick Hawes, Tom Duckett, Marc Hanheide, Tomáš Krajník
- **arXiv ID**: 1807.05196v1
- **Date**: 2018-07-13
- **URL**: [PDF Link](https://arxiv.org/pdf/1807.05196v1.pdf)

**Abstract**:

Autonomous systems will play an essential role in many applications across diverse domains including space, marine, air, field, road, and service robotics. They will assist us in our daily routines and perform dangerous, dirty and dull tasks. However, enabling robotic systems to perform autonomously in complex, real-world scenarios over extended time periods (i.e. weeks, months, or years) poses many challenges. Some of these have been investigated by sub-disciplines of Artificial Intelligence (AI) including navigation & mapping, perception, knowledge representation & reasoning, planning, interaction, and learning. The different sub-disciplines have developed techniques that, when re-integrated within an autonomous system, can enable robots to operate effectively in complex, long-term scenarios. In this paper, we survey and discuss AI techniques as 'enablers' for long-term robot autonomy, current progress in integrating these techniques within long-running robotic systems, and the future challenges and opportunities for AI in long-term autonomy.

---

### 2. Autonomous Navigation for Robot-assisted Intraluminal and Endovascular Procedures: A Systematic Review

- **Authors**: Ameya Pore, Zhen Li, Diego Dall'Alba, Albert Hernansanz, Elena De Momi, Arianna Menciassi, Alicia Casals, Jenny Denkelman, Paolo Fiorini, Emmanuel Vander Poorten
- **arXiv ID**: 2305.04027v1
- **Date**: 2023-05-06
- **URL**: [PDF Link](https://arxiv.org/pdf/2305.04027v1.pdf)

**Abstract**:

Increased demand for less invasive procedures has accelerated the adoption of Intraluminal Procedures (IP) and Endovascular Interventions (EI) performed through body lumens and vessels. As navigation through lumens and vessels is quite complex, interest grows to establish autonomous navigation techniques for IP and EI for reaching the target area. Current research efforts are directed toward increasing the Level of Autonomy (LoA) during the navigation phase. One key ingredient for autonomous navigation is Motion Planning (MP) techniques. This paper provides an overview of MP techniques categorizing them based on LoA. Our analysis investigates advances for the different clinical scenarios. Through a systematic literature analysis using the PRISMA method, the study summarizes relevant works and investigates the clinical aim, LoA, adopted MP techniques, and validation types. We identify the limitations of the corresponding MP methods and provide directions to improve the robustness of the algorithms in dynamic intraluminal environments. MP for IP and EI can be classified into four subgroups: node, sampling, optimization, and learning-based techniques, with a notable rise in learning-based approaches in recent years. One of the review's contributions is the identification of the limiting factors in IP and EI robotic systems hindering higher levels of autonomous navigation. In the future, navigation is bound to become more autonomous, placing the clinician in a supervisory position to improve control precision and reduce workload.

---

### 3. Autonomous Navigation of Underactuated Bipedal Robots in Height-Constrained Environments

- **Authors**: Zhongyu Li, Jun Zeng, Shuxiao Chen, Koushil Sreenath
- **arXiv ID**: 2109.05714v4
- **Date**: 2021-09-13
- **URL**: [PDF Link](https://arxiv.org/pdf/2109.05714v4.pdf)

**Abstract**:

Navigating a large-scaled robot in unknown and cluttered height-constrained environments is challenging. Not only is a fast and reliable planning algorithm required to go around obstacles, the robot should also be able to change its intrinsic dimension by crouching in order to travel underneath height-constrained regions. There are few mobile robots that are capable of handling such a challenge, and bipedal robots provide a solution. However, as bipedal robots have nonlinear and hybrid dynamics, trajectory planning while ensuring dynamic feasibility and safety on these robots is challenging. This paper presents an end-to-end autonomous navigation framework which leverages three layers of planners and a variable walking height controller to enable bipedal robots to safely explore height-constrained environments. A vertically-actuated Spring-Loaded Inverted Pendulum (vSLIP) model is introduced to capture the robot's coupled dynamics of planar walking and vertical walking height. This reduced-order model is utilized to optimize for long-term and short-term safe trajectory plans. A variable walking height controller is leveraged to enable the bipedal robot to maintain stable periodic walking gaits while following the planned trajectory. The entire framework is tested and experimentally validated using a bipedal robot Cassie. This demonstrates reliable autonomy to drive the robot to safely avoid obstacles while walking to the goal location in various kinds of height-constrained cluttered environments.

---

### 4. Teach and Repeat Navigation: A Robust Control Approach

- **Authors**: Payam Nourizadeh, Michael Milford, Tobias Fischer
- **arXiv ID**: 2309.15405v2
- **Date**: 2023-09-27
- **URL**: [PDF Link](https://arxiv.org/pdf/2309.15405v2.pdf)

**Abstract**:

Robot navigation requires an autonomy pipeline that is robust to environmental changes and effective in varying conditions. Teach and Repeat (T&R) navigation has shown high performance in autonomous repeated tasks under challenging circumstances, but research within T&R has predominantly focused on motion planning as opposed to motion control. In this paper, we propose a novel T&R system based on a robust motion control technique for a skid-steering mobile robot using sliding-mode control that effectively handles uncertainties that are particularly pronounced in the T&R task, where sensor noises, parametric uncertainties, and wheel-terrain interaction are common challenges. We first theoretically demonstrate that the proposed T&R system is globally stable and robust while considering the uncertainties of the closed-loop system. When deployed on a Clearpath Jackal robot, we then show the global stability of the proposed system in both indoor and outdoor environments covering different terrains, outperforming previous state-of-the-art methods in terms of mean average trajectory error and stability in these challenging environments. This paper makes an important step towards long-term autonomous T&R navigation with ensured safety guarantees.

---

### 5. Learning a Terrain- and Robot-Aware Dynamics Model for Autonomous Mobile Robot Navigation

- **Authors**: Jan Achterhold, Suresh Guttikonda, Jens U. Kreber, Haolong Li, Joerg Stueckler
- **arXiv ID**: 2409.11452v1
- **Date**: 2024-09-17
- **URL**: [PDF Link](https://arxiv.org/pdf/2409.11452v1.pdf)

**Abstract**:

Mobile robots should be capable of planning cost-efficient paths for autonomous navigation. Typically, the terrain and robot properties are subject to variations. For instance, properties of the terrain such as friction may vary across different locations. Also, properties of the robot may change such as payloads or wear and tear, e.g., causing changing actuator gains or joint friction. Autonomous navigation approaches should thus be able to adapt to such variations. In this article, we propose a novel approach for learning a probabilistic, terrain- and robot-aware forward dynamics model (TRADYN) which can adapt to such variations and demonstrate its use for navigation. Our learning approach extends recent advances in meta-learning forward dynamics models based on Neural Processes for mobile robot navigation. We evaluate our method in simulation for 2D navigation of a robot with uni-cycle dynamics with varying properties on terrain with spatially varying friction coefficients. In our experiments, we demonstrate that TRADYN has lower prediction error over long time horizons than model ablations which do not adapt to robot or terrain variations. We also evaluate our model for navigation planning in a model-predictive control framework and under various sources of noise. We demonstrate that our approach yields improved performance in planning control-efficient paths by taking robot and terrain properties into account.

---

### 6. Enhancing Autonomous Navigation by Imaging Hidden Objects using Single-Photon LiDAR

- **Authors**: Aaron Young, Nevindu M. Batagoda, Harry Zhang, Akshat Dave, Adithya Pediredla, Dan Negrut, Ramesh Raskar
- **arXiv ID**: 2410.03555v2
- **Date**: 2024-10-04
- **URL**: [PDF Link](https://arxiv.org/pdf/2410.03555v2.pdf)

**Abstract**:

Robust autonomous navigation in environments with limited visibility remains a critical challenge in robotics. We present a novel approach that leverages Non-Line-of-Sight (NLOS) sensing using single-photon LiDAR to improve visibility and enhance autonomous navigation. Our method enables mobile robots to "see around corners" by utilizing multi-bounce light information, effectively expanding their perceptual range without additional infrastructure. We propose a three-module pipeline: (1) Sensing, which captures multi-bounce histograms using SPAD-based LiDAR; (2) Perception, which estimates occupancy maps of hidden regions from these histograms using a convolutional neural network; and (3) Control, which allows a robot to follow safe paths based on the estimated occupancy. We evaluate our approach through simulations and real-world experiments on a mobile robot navigating an L-shaped corridor with hidden obstacles. Our work represents the first experimental demonstration of NLOS imaging for autonomous navigation, paving the way for safer and more efficient robotic systems operating in complex environments. We also contribute a novel dynamics-integrated transient rendering framework for simulating NLOS scenarios, facilitating future research in this domain.

---

### 7. On Deep Learning Techniques to Boost Monocular Depth Estimation for Autonomous Navigation

- **Authors**: Raul de Queiroz Mendes, Eduardo Godinho Ribeiro, Nicolas dos Santos Rosa, Valdir Grassi
- **arXiv ID**: 2010.06626v2
- **Date**: 2020-10-13
- **URL**: [PDF Link](https://arxiv.org/pdf/2010.06626v2.pdf)

**Abstract**:

Inferring the depth of images is a fundamental inverse problem within the field of Computer Vision since depth information is obtained through 2D images, which can be generated from infinite possibilities of observed real scenes. Benefiting from the progress of Convolutional Neural Networks (CNNs) to explore structural features and spatial image information, Single Image Depth Estimation (SIDE) is often highlighted in scopes of scientific and technological innovation, as this concept provides advantages related to its low implementation cost and robustness to environmental conditions. In the context of autonomous vehicles, state-of-the-art CNNs optimize the SIDE task by producing high-quality depth maps, which are essential during the autonomous navigation process in different locations. However, such networks are usually supervised by sparse and noisy depth data, from Light Detection and Ranging (LiDAR) laser scans, and are carried out at high computational cost, requiring high-performance Graphic Processing Units (GPUs). Therefore, we propose a new lightweight and fast supervised CNN architecture combined with novel feature extraction models which are designed for real-world autonomous navigation. We also introduce an efficient surface normals module, jointly with a simple geometric 2.5D loss function, to solve SIDE problems. We also innovate by incorporating multiple Deep Learning techniques, such as the use of densification algorithms and additional semantic, surface normals and depth information to train our framework. The method introduced in this work focuses on robotic applications in indoor and outdoor environments and its results are evaluated on the competitive and publicly available NYU Depth V2 and KITTI Depth datasets.

---

### 8. A Deep Learning Driven Algorithmic Pipeline for Autonomous Navigation in Row-Based Crops

- **Authors**: Simone Cerrato, Vittorio Mazzia, Francesco Salvetti, Mauro Martini, Simone Angarano, Alessandro Navone, Marcello Chiaberge
- **arXiv ID**: 2112.03816v2
- **Date**: 2021-12-07
- **URL**: [PDF Link](https://arxiv.org/pdf/2112.03816v2.pdf)

**Abstract**:

Expensive sensors and inefficient algorithmic pipelines significantly affect the overall cost of autonomous machines. However, affordable robotic solutions are essential to practical usage, and their financial impact constitutes a fundamental requirement to employ service robotics in most fields of application. Among all, researchers in the precision agriculture domain strive to devise robust and cost-effective autonomous platforms in order to provide genuinely large-scale competitive solutions. In this article, we present a complete algorithmic pipeline for row-based crops autonomous navigation, specifically designed to cope with low-range sensors and seasonal variations. Firstly, we build on a robust data-driven methodology to generate a viable path for the autonomous machine, covering the full extension of the crop with only the occupancy grid map information of the field. Moreover, our solution leverages on latest advancement of deep learning optimization techniques and synthetic generation of data to provide an affordable solution that efficiently tackles the well-known Global Navigation Satellite System unreliability and degradation due to vegetation growing inside rows. Extensive experimentation and simulations against computer-generated environments and real-world crops demonstrated the robustness and intrinsic generalizability of our methodology that opens the possibility of highly affordable and fully autonomous machines.

---

### 9. Autonomous Navigation with Mobile Robots using Deep Learning and the Robot Operating System

- **Authors**: Anh Nguyen, Quang Tran
- **arXiv ID**: 2012.02417v2
- **Date**: 2020-12-04
- **URL**: [PDF Link](https://arxiv.org/pdf/2012.02417v2.pdf)

**Abstract**:

Autonomous navigation is a long-standing field of robotics research, which provides an essential capability for mobile robots to execute a series of tasks on the same environments performed by human everyday. In this chapter, we present a set of algorithms to train and deploy deep networks for autonomous navigation of mobile robots using the Robot Operation System (ROS). We describe three main steps to tackle this problem: i) collecting data in simulation environments using ROS and Gazebo; ii) designing deep network for autonomous navigation, and iii) deploying the learned policy on mobile robots in both simulation and real-world. Theoretically, we present deep learning architectures for robust navigation in normal environments (e.g., man-made houses, roads) and complex environments (e.g., collapsed cities, or natural caves). We further show that the use of visual modalities such as RGB, Lidar, and point cloud is essential to improve the autonomy of mobile robots. Our project website and demonstration video can be found at https://sites.google.com/site/autonomousnavigationros.

---

### 10. Collection and Evaluation of a Long-Term 4D Agri-Robotic Dataset

- **Authors**: Riccardo Polvara, Sergi Molina Mellado, Ibrahim Hroob, Grzegorz Cielniak, Marc Hanheide
- **arXiv ID**: 2211.14013v1
- **Date**: 2022-11-25
- **URL**: [PDF Link](https://arxiv.org/pdf/2211.14013v1.pdf)

**Abstract**:

Long-term autonomy is one of the most demanded capabilities looked into a robot. The possibility to perform the same task over and over on a long temporal horizon, offering a high standard of reproducibility and robustness, is appealing. Long-term autonomy can play a crucial role in the adoption of robotics systems for precision agriculture, for example in assisting humans in monitoring and harvesting crops in a large orchard. With this scope in mind, we report an ongoing effort in the long-term deployment of an autonomous mobile robot in a vineyard for data collection across multiple months. The main aim is to collect data from the same area at different points in time so to be able to analyse the impact of the environmental changes in the mapping and localisation tasks. In this work, we present a map-based localisation study taking 4 data sessions. We identify expected failures when the pre-built map visually differs from the environment's current appearance and we anticipate LTS-Net, a solution pointed at extracting stable temporal features for improving long-term 4D localisation results.

---

### 11. Learning Robust Autonomous Navigation and Locomotion for Wheeled-Legged Robots

- **Authors**: Joonho Lee, Marko Bjelonic, Alexander Reske, Lorenz Wellhausen, Takahiro Miki, Marco Hutter
- **arXiv ID**: 2405.01792v1
- **Date**: 2024-05-03
- **URL**: [PDF Link](https://arxiv.org/pdf/2405.01792v1.pdf)

**Abstract**:

Autonomous wheeled-legged robots have the potential to transform logistics systems, improving operational efficiency and adaptability in urban environments. Navigating urban environments, however, poses unique challenges for robots, necessitating innovative solutions for locomotion and navigation. These challenges include the need for adaptive locomotion across varied terrains and the ability to navigate efficiently around complex dynamic obstacles. This work introduces a fully integrated system comprising adaptive locomotion control, mobility-aware local navigation planning, and large-scale path planning within the city. Using model-free reinforcement learning (RL) techniques and privileged learning, we develop a versatile locomotion controller. This controller achieves efficient and robust locomotion over various rough terrains, facilitated by smooth transitions between walking and driving modes. It is tightly integrated with a learned navigation controller through a hierarchical RL framework, enabling effective navigation through challenging terrain and various obstacles at high speed. Our controllers are integrated into a large-scale urban navigation system and validated by autonomous, kilometer-scale navigation missions conducted in Zurich, Switzerland, and Seville, Spain. These missions demonstrate the system's robustness and adaptability, underscoring the importance of integrated control systems in achieving seamless navigation in complex environments. Our findings support the feasibility of wheeled-legged robots and hierarchical RL for autonomous navigation, with implications for last-mile delivery and beyond.

---

### 12. Imperative Learning: A Self-supervised Neuro-Symbolic Learning Framework for Robot Autonomy

- **Authors**: Chen Wang, Kaiyi Ji, Junyi Geng, Zhongqiang Ren, Taimeng Fu, Fan Yang, Yifan Guo, Haonan He, Xiangyu Chen, Zitong Zhan, Qiwei Du, Shaoshu Su, Bowen Li, Yuheng Qiu, Yi Du, Qihang Li, Yifan Yang, Xiao Lin, Zhipeng Zhao
- **arXiv ID**: 2406.16087v6
- **Date**: 2024-06-23
- **URL**: [PDF Link](https://arxiv.org/pdf/2406.16087v6.pdf)

**Abstract**:

Data-driven methods such as reinforcement and imitation learning have achieved remarkable success in robot autonomy. However, their data-centric nature still hinders them from generalizing well to ever-changing environments. Moreover, labeling data for robotic tasks is often impractical and expensive. To overcome these challenges, we introduce a new self-supervised neuro-symbolic (NeSy) computational framework, imperative learning (IL), for robot autonomy, leveraging the generalization abilities of symbolic reasoning. The framework of IL consists of three primary components: a neural module, a reasoning engine, and a memory system. We formulate IL as a special bilevel optimization (BLO), which enables reciprocal learning over the three modules. This overcomes the label-intensive obstacles associated with data-driven approaches and takes advantage of symbolic reasoning concerning logical reasoning, physical principles, geometric analysis, etc. We discuss several optimization techniques for IL and verify their effectiveness in five distinct robot autonomy tasks including path planning, rule induction, optimal control, visual odometry, and multi-robot routing. Through various experiments, we show that IL can significantly enhance robot autonomy capabilities and we anticipate that it will catalyze further research across diverse domains.

---

### 13. The Reality Gap in Robotics: Challenges, Solutions, and Best Practices

- **Authors**: Elie Aljalbout, Jiaxu Xing, Angel Romero, Iretiayo Akinola, Caelan Reed Garrett, Eric Heiden, Abhishek Gupta, Tucker Hermans, Yashraj Narang, Dieter Fox, Davide Scaramuzza, Fabio Ramos
- **arXiv ID**: 2510.20808v1
- **Date**: 2025-10-23
- **URL**: [PDF Link](https://arxiv.org/pdf/2510.20808v1.pdf)

**Abstract**:

Machine learning has facilitated significant advancements across various robotics domains, including navigation, locomotion, and manipulation. Many such achievements have been driven by the extensive use of simulation as a critical tool for training and testing robotic systems prior to their deployment in real-world environments. However, simulations consist of abstractions and approximations that inevitably introduce discrepancies between simulated and real environments, known as the reality gap. These discrepancies significantly hinder the successful transfer of systems from simulation to the real world. Closing this gap remains one of the most pressing challenges in robotics. Recent advances in sim-to-real transfer have demonstrated promising results across various platforms, including locomotion, navigation, and manipulation. By leveraging techniques such as domain randomization, real-to-sim transfer, state and action abstractions, and sim-real co-training, many works have overcome the reality gap. However, challenges persist, and a deeper understanding of the reality gap's root causes and solutions is necessary. In this survey, we present a comprehensive overview of the sim-to-real landscape, highlighting the causes, solutions, and evaluation metrics for the reality gap and sim-to-real transfer.

---

### 14. Quantum Artificial Intelligence for Secure Autonomous Vehicle Navigation: An Architectural Proposal

- **Authors**: Hemanth Kannamarlapudi, Sowmya Chintalapudi
- **arXiv ID**: 2506.16000v1
- **Date**: 2025-06-19
- **URL**: [PDF Link](https://arxiv.org/pdf/2506.16000v1.pdf)

**Abstract**:

Navigation is a very crucial aspect of autonomous vehicle ecosystem which heavily relies on collecting and processing large amounts of data in various states and taking a confident and safe decision to define the next vehicle maneuver. In this paper, we propose a novel architecture based on Quantum Artificial Intelligence by enabling quantum and AI at various levels of navigation decision making and communication process in Autonomous vehicles : Quantum Neural Networks for multimodal sensor fusion, Nav-Q for Quantum reinforcement learning for navigation policy optimization and finally post-quantum cryptographic protocols for secure communication. Quantum neural networks uses quantum amplitude encoding to fuse data from various sensors like LiDAR, radar, camera, GPS and weather etc., This approach gives a unified quantum state representation between heterogeneous sensor modalities. Nav-Q module processes the fused quantum states through variational quantum circuits to learn optimal navigation policies under swift dynamic and complex conditions. Finally, post quantum cryptographic protocols are used to secure communication channels for both within vehicle communication and V2X (Vehicle to Everything) communications and thus secures the autonomous vehicle communication from both classical and quantum security threats. Thus, the proposed framework addresses fundamental challenges in autonomous vehicles navigation by providing quantum performance and future proof security. Index Terms Quantum Computing, Autonomous Vehicles, Sensor Fusion

---

### 15. Real-Time Neuromorphic Navigation: Guiding Physical Robots with Event-Based Sensing and Task-Specific Reconfigurable Autonomy Stack

- **Authors**: Sourav Sanyal, Amogh Joshi, Adarsh Kosta, Kaushik Roy
- **arXiv ID**: 2503.09636v1
- **Date**: 2025-03-11
- **URL**: [PDF Link](https://arxiv.org/pdf/2503.09636v1.pdf)

**Abstract**:

Neuromorphic vision, inspired by biological neural systems, has recently gained significant attention for its potential in enhancing robotic autonomy. This paper presents a systematic exploration of a proposed Neuromorphic Navigation framework that uses event-based neuromorphic vision to enable efficient, real-time navigation in robotic systems. We discuss the core concepts of neuromorphic vision and navigation, highlighting their impact on improving robotic perception and decision-making. The proposed reconfigurable Neuromorphic Navigation framework adapts to the specific needs of both ground robots (Turtlebot) and aerial robots (Bebop2 quadrotor), addressing the task-specific design requirements (algorithms) for optimal performance across the autonomous navigation stack -- Perception, Planning, and Control. We demonstrate the versatility and the effectiveness of the framework through two case studies: a Turtlebot performing local replanning for real-time navigation and a Bebop2 quadrotor navigating through moving gates. Our work provides a scalable approach to task-specific, real-time robot autonomy leveraging neuromorphic systems, paving the way for energy-efficient autonomous navigation.

---

### 16. Robotics Under Construction: Challenges on Job Sites

- **Authors**: Haruki Uchiito, Akhilesh Bhat, Koji Kusaka, Xiaoya Zhang, Hiraku Kinjo, Honoka Uehara, Motoki Koyama, Shinji Natsume
- **arXiv ID**: 2506.19597v1
- **Date**: 2025-06-24
- **URL**: [PDF Link](https://arxiv.org/pdf/2506.19597v1.pdf)

**Abstract**:

As labor shortages and productivity stagnation increasingly challenge the construction industry, automation has become essential for sustainable infrastructure development. This paper presents an autonomous payload transportation system as an initial step toward fully unmanned construction sites. Our system, based on the CD110R-3 crawler carrier, integrates autonomous navigation, fleet management, and GNSS-based localization to facilitate material transport in construction site environments. While the current system does not yet incorporate dynamic environment adaptation algorithms, we have begun fundamental investigations into external-sensor based perception and mapping system. Preliminary results highlight the potential challenges, including navigation in evolving terrain, environmental perception under construction-specific conditions, and sensor placement optimization for improving autonomy and efficiency. Looking forward, we envision a construction ecosystem where collaborative autonomous agents dynamically adapt to site conditions, optimizing workflow and reducing human intervention. This paper provides foundational insights into the future of robotics-driven construction automation and identifies critical areas for further technological development.

---

### 17. Autonomous Teamed Exploration of Subterranean Environments using Legged and Aerial Robots

- **Authors**: Mihir Kulkarni, Mihir Dharmadhikari, Marco Tranzatto, Samuel Zimmermann, Victor Reijgwart, Paolo De Petris, Huan Nguyen, Nikhil Khedekar, Christos Papachristos, Lionel Ott, Roland Siegwart, Marco Hutter, Kostas Alexis
- **arXiv ID**: 2111.06482v2
- **Date**: 2021-11-11
- **URL**: [PDF Link](https://arxiv.org/pdf/2111.06482v2.pdf)

**Abstract**:

This paper presents a novel strategy for autonomous teamed exploration of subterranean environments using legged and aerial robots. Tailored to the fact that subterranean settings, such as cave networks and underground mines, often involve complex, large-scale and multi-branched topologies, while wireless communication within them can be particularly challenging, this work is structured around the synergy of an onboard exploration path planner that allows for resilient long-term autonomy, and a multi-robot coordination framework. The onboard path planner is unified across legged and flying robots and enables navigation in environments with steep slopes, and diverse geometries. When a communication link is available, each robot of the team shares submaps to a centralized location where a multi-robot coordination framework identifies global frontiers of the exploration space to inform each system about where it should re-position to best continue its mission. The strategy is verified through a field deployment inside an underground mine in Switzerland using a legged and a flying robot collectively exploring for 45 min, as well as a longer simulation study with three systems.

---

### 18. NeBula: Quest for Robotic Autonomy in Challenging Environments; TEAM CoSTAR at the DARPA Subterranean Challenge

- **Authors**: Ali Agha, Kyohei Otsu, Benjamin Morrell, David D. Fan, Rohan Thakker, Angel Santamaria-Navarro, Sung-Kyun Kim, Amanda Bouman, Xianmei Lei, Jeffrey Edlund, Muhammad Fadhil Ginting, Kamak Ebadi, Matthew Anderson, Torkom Pailevanian, Edward Terry, Michael Wolf, Andrea Tagliabue, Tiago Stegun Vaquero, Matteo Palieri, Scott Tepsuporn, Yun Chang, Arash Kalantari, Fernando Chavez, Brett Lopez, Nobuhiro Funabiki, Gregory Miles, Thomas Touma, Alessandro Buscicchio, Jesus Tordesillas, Nikhilesh Alatur, Jeremy Nash, William Walsh, Sunggoo Jung, Hanseob Lee, Christoforos Kanellakis, John Mayo, Scott Harper, Marcel Kaufmann, Anushri Dixit, Gustavo Correa, Carlyn Lee, Jay Gao, Gene Merewether, Jairo Maldonado-Contreras, Gautam Salhotra, Maira Saboia Da Silva, Benjamin Ramtoula, Yuki Kubo, Seyed Fakoorian, Alexander Hatteland, Taeyeon Kim, Tara Bartlett, Alex Stephens, Leon Kim, Chuck Bergh, Eric Heiden, Thomas Lew, Abhishek Cauligi, Tristan Heywood, Andrew Kramer, Henry A. Leopold, Chris Choi, Shreyansh Daftry, Olivier Toupet, Inhwan Wee, Abhishek Thakur, Micah Feras, Giovanni Beltrame, George Nikolakopoulos, David Shim, Luca Carlone, Joel Burdick
- **arXiv ID**: 2103.11470v4
- **Date**: 2021-03-21
- **URL**: [PDF Link](https://arxiv.org/pdf/2103.11470v4.pdf)

**Abstract**:

This paper presents and discusses algorithms, hardware, and software architecture developed by the TEAM CoSTAR (Collaborative SubTerranean Autonomous Robots), competing in the DARPA Subterranean Challenge. Specifically, it presents the techniques utilized within the Tunnel (2019) and Urban (2020) competitions, where CoSTAR achieved 2nd and 1st place, respectively. We also discuss CoSTAR's demonstrations in Martian-analog surface and subsurface (lava tubes) exploration. The paper introduces our autonomy solution, referred to as NeBula (Networked Belief-aware Perceptual Autonomy). NeBula is an uncertainty-aware framework that aims at enabling resilient and modular autonomy solutions by performing reasoning and decision making in the belief space (space of probability distributions over the robot and world states). We discuss various components of the NeBula framework, including: (i) geometric and semantic environment mapping; (ii) a multi-modal positioning system; (iii) traversability analysis and local planning; (iv) global motion planning and exploration behavior; (i) risk-aware mission planning; (vi) networking and decentralized reasoning; and (vii) learning-enabled adaptation. We discuss the performance of NeBula on several robot types (e.g. wheeled, legged, flying), in various environments. We discuss the specific results and lessons learned from fielding this solution in the challenging courses of the DARPA Subterranean Challenge competition.

---

### 19. Ariel Explores: Vision-based underwater exploration and inspection via generalist drone-level autonomy

- **Authors**: Mohit Singh, Mihir Dharmadhikari, Kostas Alexis
- **arXiv ID**: 2507.10003v1
- **Date**: 2025-07-14
- **URL**: [PDF Link](https://arxiv.org/pdf/2507.10003v1.pdf)

**Abstract**:

This work presents a vision-based underwater exploration and inspection autonomy solution integrated into Ariel, a custom vision-driven underwater robot. Ariel carries a $5$ camera and IMU based sensing suite, enabling a refraction-aware multi-camera visual-inertial state estimation method aided by a learning-based proprioceptive robot velocity prediction method that enhances robustness against visual degradation. Furthermore, our previously developed and extensively field-verified autonomous exploration and general visual inspection solution is integrated on Ariel, providing aerial drone-level autonomy underwater. The proposed system is field-tested in a submarine dry dock in Trondheim under challenging visual conditions. The field demonstration shows the robustness of the state estimation solution and the generalizability of the path planning techniques across robot embodiments.

---

### 20. Assurance for Autonomy -- JPL's past research, lessons learned, and future directions

- **Authors**: Martin S. Feather, Alessandro Pinto
- **arXiv ID**: 2305.11902v1
- **Date**: 2023-05-16
- **URL**: [PDF Link](https://arxiv.org/pdf/2305.11902v1.pdf)

**Abstract**:

Robotic space missions have long depended on automation, defined in the 2015 NASA Technology Roadmaps as "the automatically-controlled operation of an apparatus, process, or system using a pre-planned set of instructions (e.g., a command sequence)," to react to events when a rapid response is required. Autonomy, defined there as "the capacity of a system to achieve goals while operating independently from external control," is required when a wide variation in circumstances precludes responses being pre-planned, instead autonomy follows an on-board deliberative process to determine the situation, decide the response, and manage its execution. Autonomy is increasingly called for to support adventurous space mission concepts, as an enabling capability or as a significant enhancer of the science value that those missions can return. But if autonomy is to be allowed to control these missions' expensive assets, all parties in the lifetime of a mission, from proposers through ground control, must have high confidence that autonomy will perform as intended to keep the asset safe to (if possible) accomplish the mission objectives. The role of mission assurance is a key contributor to providing this confidence, yet assurance practices honed over decades of spaceflight have relatively little experience with autonomy. To remedy this situation, researchers in JPL's software assurance group have been involved in the development of techniques specific to the assurance of autonomy. This paper summarizes over two decades of this research, and offers a vision of where further work is needed to address open issues.

---

